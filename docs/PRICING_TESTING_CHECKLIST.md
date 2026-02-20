# Pricing Integration Testing Checklist

## 📋 Pre-Testing Setup

### Environment Configuration
- [ ] `.env` file has `MAIN_API_URL=https://staging.pixorasoft.ru`
- [ ] `.env` file has `MAIN_URL=https://staging.pixorasoft.ru`
- [ ] Backend server is running
- [ ] Pixora main API is accessible

### Database Setup
- [ ] Test session exists in Pixora database
- [ ] Test session has `facepass_enabled = true`
- [ ] Test session has services/packages configured
- [ ] At least one service has `isDefault = true`
- [ ] At least one service has `type = 'digital'`

## 🔍 Backend Testing

### 1. Template Variable Injection

**Test:** Open session interface page and check source code

```bash
# Method 1: Browser
1. Navigate to: https://facepass.pixorasoft.ru/api/v1/sessions/{session_id}/interface
2. Press Ctrl+U (View Source)
3. Search for "window.MAIN_API_URL"
4. Verify it shows: window.MAIN_API_URL = "https://staging.pixorasoft.ru";
```

**Expected Result:**
```html
<script>
    window.MAIN_API_URL = "https://staging.pixorasoft.ru";
</script>
```

**❌ Failure Indicators:**
- Shows: `window.MAIN_API_URL = "{{ MAIN_API_URL }}";`
- Shows: `window.MAIN_API_URL = "";`
- Variable is missing entirely

**Fix:** Check `app/api/v1/endpoints/sessions.py` lines 265-285

---

### 2. Backend Logs

**Test:** Check server logs for replacement confirmation

```bash
# Start server with logging
uvicorn app.main:app --reload --log-level info

# Look for these log messages:
# INFO: Replaced '"{{ MAIN_API_URL }}"' with '"https://staging.pixorasoft.ru"'
# INFO: Serving interface for session {id} with MAIN_API_URL: https://staging.pixorasoft.ru
```

**Expected Result:**
- Log shows successful replacement
- No warnings about template not found

**❌ Failure Indicators:**
- Warning: "MAIN_API_URL template not found in HTML"
- No replacement log messages

---

## 🌐 Frontend Testing

### 3. Browser Console Check

**Test:** Open DevTools Console on session page

```javascript
// Check if variable is defined
console.log('MAIN_API_URL:', window.MAIN_API_URL);

// Check if it contains template syntax
console.log('Has template:', 
    window.MAIN_API_URL.includes('{{') || 
    window.MAIN_API_URL.includes('}}')
);
```

**Expected Result:**
```
MAIN_API_URL: https://staging.pixorasoft.ru
Has template: false
```

**❌ Failure Indicators:**
```
MAIN_API_URL: {{ MAIN_API_URL }}
Has template: true
```

---

### 4. Services API Call

**Test:** Monitor Network tab for API request

```bash
# Steps:
1. Open DevTools → Network tab
2. Filter by "services"
3. Upload a selfie and perform search
4. Look for request to: /api/session/{id}/services
```

**Expected Result:**
- Request URL: `https://staging.pixorasoft.ru/api/session/{id}/services`
- Status: 200 OK
- Response contains services array
- Response has `price_single` and `price_all` values

**❌ Failure Indicators:**
- Request URL contains `{{ MAIN_API_URL }}`
- Status: 404 Not Found
- Status: 0 (CORS error)
- Empty services array

---

### 5. Price Display

**Test:** Verify prices appear on photo cards

```bash
# Steps:
1. Upload selfie
2. Wait for search results
3. Check photo cards for price badges
```

**Expected Result:**
- Skeleton loader appears first (gray pulsing badge)
- After ~1-2 seconds, real prices appear
- Price badges show: "150 ₽" (or actual price)
- Gradient background: indigo to purple

**❌ Failure Indicators:**
- Skeleton loader never disappears
- No price badges visible
- Price shows "0 ₽"
- Console errors about services

---

### 6. Floating Purchase Bar

**Test:** Verify floating bar appears with correct prices

```bash
# Steps:
1. Perform search and get results
2. Check bottom of screen for floating bar
3. Select some photos
4. Verify price calculation
```

**Expected Result:**
- Floating bar visible at bottom
- Shows "Выбрано фото: X"
- Shows "Итого: Y ₽"
- "Купить выбранные" button enabled when photos selected
- "Купить весь архив" button always enabled

**❌ Failure Indicators:**
- Floating bar hidden
- Price shows "0 ₽"
- Buttons disabled
- Console error: "Services not available"

---

### 7. View-Only Mode

**Test:** Verify graceful degradation when services unavailable

```bash
# Simulate by:
1. Temporarily break CORS on Pixora API
2. Or use invalid session ID
3. Perform search
```

**Expected Result:**
- No price badges on photos
- No floating purchase bar
- Photos still viewable
- No JavaScript errors
- Console log: "Running in view-only mode"

**❌ Failure Indicators:**
- JavaScript errors in console
- Page breaks or doesn't load
- Skeleton loaders stuck forever

---

## 🔗 CORS Testing

### 8. CORS Headers

**Test:** Verify CORS is configured on Pixora API

```bash
# Method 1: curl
curl -I -X OPTIONS \
  -H "Origin: https://facepass.pixorasoft.ru" \
  -H "Access-Control-Request-Method: GET" \
  https://staging.pixorasoft.ru/api/session/test/services

# Method 2: Browser DevTools
# Network tab → Look for OPTIONS request
# Check Response Headers
```

**Expected Result:**
```
Access-Control-Allow-Origin: https://facepass.pixorasoft.ru
Access-Control-Allow-Methods: GET, OPTIONS
Access-Control-Allow-Headers: Accept, Content-Type
```

**❌ Failure Indicators:**
- No CORS headers present
- Status: 0 in Network tab
- Console error: "CORS policy blocked"

---

## 🛒 Purchase Flow Testing

### 9. Buy Selected Photos

**Test:** Verify redirect to cart with selected photos

```bash
# Steps:
1. Perform search
2. Select 3 photos
3. Click "Купить выбранные"
```

**Expected Result:**
- Redirects to: `https://staging.pixorasoft.ru/session/{id}/cart?selected=id1,id2,id3&source=facepass`
- Toast notification: "Переход к покупке 3 фотографий"

**❌ Failure Indicators:**
- No redirect
- Wrong URL format
- Missing photo IDs
- 404 error on cart page

---

### 10. Buy Full Archive

**Test:** Verify redirect to cart with package

```bash
# Steps:
1. Perform search
2. Click "Купить весь архив"
```

**Expected Result:**
- Redirects to: `https://staging.pixorasoft.ru/session/{id}/cart?package=digital&source=facepass`
- Toast notification: "Переход к покупке всего архива"

**❌ Failure Indicators:**
- No redirect
- Wrong URL format
- Missing package parameter
- 404 error on cart page

---

## 📱 Mobile Testing

### 11. Mobile Price Display

**Test:** Verify pricing works on mobile devices

```bash
# Steps:
1. Open on mobile device or use DevTools mobile emulation
2. Perform search
3. Check price badges and floating bar
```

**Expected Result:**
- Price badges visible and readable
- Floating bar adapts to mobile layout
- Touch targets are adequate (48px minimum)
- No horizontal scrolling

**❌ Failure Indicators:**
- Price badges cut off
- Floating bar overlaps content
- Buttons too small to tap
- Layout breaks

---

## 🧪 Automated Testing

### 12. Use Test Page

**Test:** Run automated test suite

```bash
# Open test page
https://facepass.pixorasoft.ru/tests/ui/test_pricing_integration.html

# Or locally
open tests/ui/test_pricing_integration.html
```

**Expected Result:**
- All tests show green checkmarks
- Configuration check passes
- Template injection test passes
- API endpoint test returns services

**❌ Failure Indicators:**
- Red error messages
- Template not replaced warning
- API call fails
- CORS errors

---

## 📊 Performance Testing

### 13. Load Time

**Test:** Measure time to display prices

```bash
# Use DevTools Performance tab
1. Start recording
2. Upload selfie
3. Wait for prices to appear
4. Stop recording
```

**Expected Result:**
- Services loaded in < 2 seconds
- Skeleton visible for 1-2 seconds
- Smooth transition to real prices
- No layout shift

**❌ Failure Indicators:**
- Services take > 5 seconds
- Skeleton stuck forever
- Layout jumps when prices load

---

## 🔄 Edge Cases

### 14. No Services Available

**Test:** Session with no services configured

**Expected Result:**
- View-only mode activated
- No price badges
- No floating bar
- Photos still searchable

---

### 15. Invalid Session

**Test:** Non-existent session ID

**Expected Result:**
- Error page: "Сессия не найдена"
- No JavaScript errors

---

### 16. FacePass Disabled

**Test:** Session with `facepass_enabled = false`

**Expected Result:**
- Error page: "FacePass не активен"
- No access to interface

---

## ✅ Final Checklist

Before deploying to production:

- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] CORS configured correctly
- [ ] Template injection working
- [ ] Prices display correctly
- [ ] Purchase flow works
- [ ] Mobile layout correct
- [ ] View-only mode works
- [ ] Performance acceptable
- [ ] Edge cases handled
- [ ] Documentation updated
- [ ] Logs show no errors

---

## 🐛 Common Issues & Solutions

### Issue: Template not replaced

**Symptoms:** `window.MAIN_API_URL = "{{ MAIN_API_URL }}"`

**Solution:**
1. Check `.env` has `MAIN_API_URL` set
2. Restart backend server
3. Check `sessions.py` replacement logic
4. Verify `get_settings()` returns correct value

---

### Issue: CORS blocked

**Symptoms:** Status 0, "CORS policy blocked" in console

**Solution:**
1. Configure CORS on Pixora API
2. Add `https://facepass.pixorasoft.ru` to allowed origins
3. Allow GET and OPTIONS methods
4. Test with curl

---

### Issue: Services not loading

**Symptoms:** Skeleton loader stuck, no prices

**Solution:**
1. Check Pixora API is running
2. Verify endpoint exists: `/api/session/{id}/services`
3. Check response format matches spec
4. Verify session has services in database

---

### Issue: Wrong prices

**Symptoms:** Prices show 0 or incorrect values

**Solution:**
1. Check `getServicePrices()` logic
2. Verify services have `isDefault` and `type` fields
3. Check database has correct prices
4. Console log the services response

---

## 📞 Support

If tests fail:
1. Check this checklist systematically
2. Review console logs (browser and server)
3. Check Network tab for failed requests
4. Verify database configuration
5. See `docs/REAL_TIME_PRICING_SUMMARY.md` for architecture

---

**Last Updated:** 2026-02-20
**Version:** 1.0
