# Neighborhood Coordinate Fix Script

## Overview
This script fixes incorrect neighborhood coordinates in the database by validating them against Google Places API and updating any coordinates that are significantly wrong (>2km difference).

## Usage

### 1. Prerequisites
- Ensure your Google Maps API key is set in environment variables
- The key should have access to Places API (Text Search)
- Make sure you have database access configured

### 2. Run the Script
```bash
cd backend
python fix_neighborhood_coordinates.py
```

### 3. What the Script Does
1. **Validates** each neighborhood's coordinates using Google Places API
2. **Compares** database coordinates with Google's results
3. **Updates** coordinates that differ by more than 2km
4. **Reports** all changes made and any errors encountered

### 4. Expected Output
```
⚠️  WARNING: This script will modify neighborhood coordinates in the database
🔄 It will make Google Places API calls for each neighborhood
💰 This may incur API usage costs

Do you want to continue? (y/N): y

🚀 Starting coordinate fixing process...

🗺️  Neighborhood Coordinate Fixer
============================================================
Using Google API Key: AIzaSyBGK9...

📊 Found 61 neighborhoods to validate

[ 1/61] Processing: אורות
   ✅ Found coordinates for 'אורות תל אביב יפו': (32.057, 34.806)
   📏 Distance from database: 50 meters
   ✅ Coordinates are accurate (within 2km)

[ 2/61] Processing: מכללת יפו תל אביב ודקר
   ✅ Found coordinates for 'מכללת יפו תל אביב ודקר תל אביב יפו': (32.0421681, 34.7588906)
   📏 Distance from database: 4500 meters
   🔧 CORRECTION NEEDED:
      📍 Old: (32.0852999, 34.7817676)
      🌐 New: (32.0421681, 34.7588906)
      ✅ Updated in database

...

💾 All changes committed to database

============================================================
📋 SUMMARY REPORT
============================================================
🔧 Corrections made: 3
🌐 API calls made: 85
❌ Errors encountered: 0

📝 DETAILED CORRECTIONS:
   🏘️  מכללת יפו תל אביב ודקר (ID: 496)
      📍 (32.0852999, 34.7817676) → (32.0421681, 34.7588906)
      📏 Distance: 4500 meters

✅ Coordinate fixing completed!
🎯 Transit times should now be more accurate across all neighborhoods
```

## Impact on Transit Times

### Before Fix
- Some neighborhoods had coordinates from wrong locations
- Example: דקר neighborhood was using central Tel Aviv coordinates
- This caused transit times to be completely wrong (12 min instead of 30+ min)

### After Fix
- All neighborhoods use accurate coordinates
- Transit times will match Google Maps mobile
- Location-based recommendations become reliable

## Cost Considerations
- The script makes one Places API call per neighborhood (~60-100 calls)
- Each call costs approximately $0.032 (Text Search pricing)
- Total estimated cost: ~$2-3 for the entire database
- This is a one-time cost that improves accuracy permanently

## Frequency
- **Run once**: After initial setup or when adding new neighborhoods
- **Rerun**: Only if you suspect coordinate accuracy issues
- **Not needed**: For regular operation - coordinates are now accurate

## Safety Features
- ✅ **Confirmation prompt** before making any changes
- ✅ **2km threshold** - only fixes significant errors
- ✅ **Detailed logging** of all changes
- ✅ **Database transaction** - all changes committed together
- ✅ **Error handling** - continues processing even if some fail

## After Running
1. **Remove API calls**: The recommendation service no longer makes coordinate validation calls
2. **Faster performance**: No runtime API calls for coordinates
3. **Accurate results**: All transit times based on correct locations
4. **Cost effective**: One-time fix vs continuous API calls

## Troubleshooting

### "No API key" Error
```bash
❌ ERROR: GOOGLE_API_KEY not set in environment variables
```
Solution: Set your Google Maps API key in environment variables

### "REQUEST_DENIED" Errors
- Check that Places API is enabled in Google Cloud Console
- Verify API key has necessary permissions
- Ensure billing is set up for the project

### Database Connection Issues
- Verify DATABASE_URL is set correctly
- Check database credentials and connectivity
- Ensure you have write permissions
