#!/bin/bash
# ══════════════════════════════════════════════════════
#  FastNest API Test Script
#  Usage: chmod +x api_test.sh && ./api_test.sh
# ══════════════════════════════════════════════════════

BASE="http://localhost:8000"
if [ -z "$DB_URL" ]; then
  echo "  ❌ DB_URL is not set. Export it (see example/.env.example) before running this script."
  exit 1
fi
SEP="─────────────────────────────────────────"
PASS=0; FAIL=0

# ── Reset & re-seed DB before running tests ──────────
echo "$SEP"
echo "  Resetting database..."
psql "$DB_URL" -q << 'SQL'
TRUNCATE posts, refresh_tokens, users RESTART IDENTITY CASCADE;
-- password_hash/password_salt = PBKDF2-HMAC-SHA256("secret123"), see schema.sql
INSERT INTO users (name, email, password_hash, password_salt, roles) VALUES
    ('Admin User',   'admin@fastnest.dev', 'ae1a300122076fa9431f3e5cf7f0f195f0c9bde2b90ab0151efbf40d7e1f1806', '0a590ebd44abd760ab2e9ddce718b0f9', '{admin,user}'),
    ('Regular User', 'user@fastnest.dev',  'ae1a300122076fa9431f3e5cf7f0f195f0c9bde2b90ab0151efbf40d7e1f1806', '0a590ebd44abd760ab2e9ddce718b0f9', '{user}'),
    ('Moderator',    'mod@fastnest.dev',   'ae1a300122076fa9431f3e5cf7f0f195f0c9bde2b90ab0151efbf40d7e1f1806', '0a590ebd44abd760ab2e9ddce718b0f9', '{moderator,user}');
INSERT INTO posts (title, content, author_id)
SELECT 'Post ' || g, 'Content of post ' || g, (SELECT id FROM users WHERE email = 'admin@fastnest.dev')
FROM generate_series(1, 3) g;
SQL
if [ $? -eq 0 ]; then
  echo "  ✅ DB reset and seeded"
else
  echo "  ❌ DB reset failed — check DB_URL and connection"
  echo "  DB_URL=$DB_URL"
  exit 1
fi
echo "$SEP"

ok()     { echo "  ✅ $1"; ((PASS++)); }
fail()   { echo "  ❌ $1"; ((FAIL++)); }
header() { echo -e "\n$SEP\n  $1\n$SEP"; }
json()   { echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"; }
field()  { echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d$2)" 2>/dev/null; }

# ── 1. REGISTER ──────────────────────────────────────
header "1. Register new user"
# delete test user first if exists (idempotent run)
RAND_EMAIL="newtest_$(date +%s)_$$@test.com"
RES=$(curl -s -w "\n%{http_code}" -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Test User\",\"email\":\"$RAND_EMAIL\",\"password\":\"pass123\"}")
BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
if [ "$CODE" = "200" ]; then
  ok "Registered: $(field "$BODY" "['name']") (HTTP $CODE)"
else
  fail "Register HTTP $CODE: $BODY"
fi

# ── 2. LOGIN AS ADMIN ────────────────────────────────
header "2. Login as admin (password: secret123)"
RES=$(curl -s -w "\n%{http_code}" -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@fastnest.dev","password":"secret123"}')
BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
ADMIN_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ "$CODE" = "200" ] && [ -n "$ADMIN_TOKEN" ]; then
  ok "Admin login OK — token received"
else
  fail "Admin login HTTP $CODE: $BODY"
  echo "  ⚠️  Remaining tests will fail without admin token"
fi

# ── 3. LOGIN AS REGULAR USER ─────────────────────────
header "3. Login as regular user (password: secret123)"
RES=$(curl -s -w "\n%{http_code}" -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@fastnest.dev","password":"secret123"}')
BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
USER_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

[ "$CODE" = "200" ] && [ -n "$USER_TOKEN" ] \
  && ok "User login OK — token received" \
  || fail "User login HTTP $CODE: $BODY"

# ── 4. GET MY PROFILE ────────────────────────────────
header "4. GET /auth/me"
RES=$(curl -s -w "\n%{http_code}" $BASE/auth/me \
  -H "Authorization: Bearer $USER_TOKEN")
BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
[ "$CODE" = "200" ] \
  && ok "Profile: $(field "$BODY" "['name']") | roles: $(field "$BODY" "['roles']")" \
  || fail "GET /auth/me HTTP $CODE: $BODY"

# ── 5. LIST ALL USERS (admin) ────────────────────────
header "5. GET /users  (admin sees all, user gets 403)"
RES=$(curl -s -w "\n%{http_code}" "$BASE/users?page=1&limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
[ "$CODE" = "200" ] \
  && ok "Admin sees users — total: $(field "$BODY" "['total']")" \
  || fail "Admin list HTTP $CODE: $BODY"

# regular user should get 403
RES2=$(curl -s -w "\n%{http_code}" "$BASE/users" \
  -H "Authorization: Bearer $USER_TOKEN")
CODE2=$(echo "$RES2" | tail -1)
[ "$CODE2" = "403" ] \
  && ok "Regular user correctly blocked (403)" \
  || fail "Expected 403, got $CODE2"

# ── 6. FIND BY ROLE ──────────────────────────────────
header "6. GET /users/by-role?role=admin"
RES=$(curl -s -w "\n%{http_code}" "$BASE/users/by-role?role=admin" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
if [ "$CODE" = "200" ]; then
  COUNT=$(echo "$BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
  ok "Found $COUNT admin(s)"
  echo "$BODY" | python3 -c "
import sys,json
for u in json.load(sys.stdin):
    print(f'     → {u[\"name\"]:20s} roles={u[\"roles\"]}')
" 2>/dev/null
else
  fail "by-role HTTP $CODE: $BODY"
fi

# ── 7. CREATE USER (admin) ───────────────────────────
header "7. POST /users  (admin creates with roles)"
RES=$(curl -s -w "\n%{http_code}" -X POST $BASE/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Role Tester","email":"roletester@test.com","password":"pass123","roles":["admin","user"]}')
BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
NEW_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)

[ "$CODE" = "200" ] && [ -n "$NEW_ID" ] \
  && ok "Created: $(field "$BODY" "['name']") | roles: $(field "$BODY" "['roles']")" \
  || fail "Create user HTTP $CODE: $BODY"

# ── 8. CHECK ROLE ────────────────────────────────────
header "8. GET /users/:id/check-role?role=admin"
if [ -n "$NEW_ID" ]; then
  RES=$(curl -s -w "\n%{http_code}" "$BASE/users/$NEW_ID/check-role?role=admin" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
  [ "$CODE" = "200" ] \
    && ok "has_role=admin: $(field "$BODY" "['has_role']") | all_roles: $(field "$BODY" "['all_roles']")" \
    || fail "check-role HTTP $CODE: $BODY"
else
  fail "Skipped — no user ID"
fi

# ── 9. PATCH ROLES ───────────────────────────────────
header "9. PATCH /users/:id/roles  (downgrade admin → user)"
if [ -n "$NEW_ID" ]; then
  RES=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE/users/$NEW_ID/roles" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"roles":["user"]}')
  BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
  [ "$CODE" = "200" ] \
    && ok "Roles updated → $(field "$BODY" "['roles']")" \
    || fail "PATCH roles HTTP $CODE: $BODY"

  # verify
  RES2=$(curl -s "$BASE/users/$NEW_ID/check-role?role=admin" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  HAS=$(echo "$RES2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('has_role','?'))" 2>/dev/null)
  [ "$HAS" = "False" ] \
    && ok "Verified: has_role=admin is now False" \
    || fail "Expected False, got: $HAS — $RES2"
fi

# ── 10. UPDATE USER ──────────────────────────────────
header "10. PUT /users/:id  (update name)"
if [ -n "$NEW_ID" ]; then
  RES=$(curl -s -w "\n%{http_code}" -X PUT "$BASE/users/$NEW_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"Updated Tester"}')
  BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
  [ "$CODE" = "200" ] \
    && ok "Name updated → $(field "$BODY" "['name']")" \
    || fail "PUT user HTTP $CODE: $BODY"
fi

# ── 11. DELETE USER ──────────────────────────────────
header "11. DELETE /users/:id"
if [ -n "$NEW_ID" ]; then
  RES=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE/users/$NEW_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
  [ "$CODE" = "200" ] \
    && ok "$(field "$BODY" "['message']")" \
    || fail "DELETE user HTTP $CODE: $BODY"

  # confirm gone
  RES2=$(curl -s -w "\n%{http_code}" "$BASE/users/$NEW_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  CODE2=$(echo "$RES2" | tail -1)
  [ "$CODE2" = "404" ] && ok "Confirmed: user no longer exists (404)" || fail "Expected 404, got $CODE2"
fi

# ── 12. POSTS CRUD ───────────────────────────────────
header "12. Posts CRUD"
# create
RES=$(curl -s -w "\n%{http_code}" -X POST $BASE/posts \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"My First Post","content":"Hello from FastNest + PostgreSQL!"}')
BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
POST_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
[ "$CODE" = "200" ] && [ -n "$POST_ID" ] \
  && ok "Post created: $(field "$BODY" "['title']")" \
  || fail "Create post HTTP $CODE: $BODY"

# update own
if [ -n "$POST_ID" ]; then
  RES=$(curl -s -w "\n%{http_code}" -X PUT "$BASE/posts/$POST_ID" \
    -H "Authorization: Bearer $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"title":"Updated Title"}')
  BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
  [ "$CODE" = "200" ] \
    && ok "Post updated → $(field "$BODY" "['title']")" \
    || fail "Update post HTTP $CODE: $BODY"

  # admin deletes user's post (ownership override)
  RES=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE/posts/$POST_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
  [ "$CODE" = "200" ] \
    && ok "Admin deleted user post: $(field "$BODY" "['message']")" \
    || fail "Admin delete post HTTP $CODE: $BODY"
fi

# ── 13. FORBIDDEN — user tries to delete another's post ──
header "13. Authorization — user cannot delete admin's post"
ADMIN_POST=$(curl -s "$BASE/posts" -H "Authorization: Bearer $ADMIN_TOKEN" \
  | python3 -c "import sys,json; posts=json.load(sys.stdin); print(posts[0]['id'] if posts else '')" 2>/dev/null)
if [ -n "$ADMIN_POST" ]; then
  RES=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE/posts/$ADMIN_POST" \
    -H "Authorization: Bearer $USER_TOKEN")
  CODE=$(echo "$RES" | tail -1)
  [ "$CODE" = "403" ] \
    && ok "Correctly blocked (403) — cannot delete others' posts" \
    || fail "Expected 403, got $CODE"
fi

# ── 14. VALIDATION ERRORS ────────────────────────────
header "14. Validation — bad roles & short password"
RES=$(curl -s -w "\n%{http_code}" -X POST $BASE/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"X","email":"x@x.com","password":"123","roles":["superadmin"]}')
BODY=$(echo "$RES" | head -1); CODE=$(echo "$RES" | tail -1)
[ "$CODE" = "422" ] \
  && ok "Validation rejected (422 Unprocessable Entity)" \
  || fail "Expected 422, got $CODE: $BODY"
echo "$BODY" | python3 -c "
import sys,json
d=json.load(sys.stdin)
errs = d.get('detail',{}).get('errors',[])
for e in errs:
    print(f'     field={e[\"field\"]} → {e[\"message\"]}')
" 2>/dev/null

# ── SUMMARY ──────────────────────────────────────────
echo -e "\n$SEP"
echo "  Results: ✅ $PASS passed   ❌ $FAIL failed"
echo "$SEP"
