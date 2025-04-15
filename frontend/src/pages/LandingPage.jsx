import React from 'react';
import houseIllustration from '../assets/house_illustration.svg';
import logoIcon from '../assets/logo_icon.svg';
import slogen from '../assets/slogen.svg';

function LandingPage() {
  return (
    <div className="min-h-screen bg-[#AEAFF7] flex flex-col items-center justify-center p-6">
      <div className="text-center mb-8">
        {/* לוגו */}
        <div className="flex items-center justify-center mb-2">
          <img src={logoIcon} alt="APT Scanner logo icon" className="h-8 w-8 mr-2" />
        </div>
        {/* סלוגן */}
        <img src={slogen} alt="APT Scanner slogen" className="h-8 w-8 mr-2" />
      </div>

      {/* איור מרכזי */}
      <div className="mb-12">
        <img src={houseIllustration} alt="House illustration" className="max-w-xs mx-auto" />
      </div>

      {/* אזור תחתון: כפתורים/פעולות */}
      <div className="w-full max-w-xs">
        {/* כפתור הרשמה */}
        <button className="w-full bg-gray-800 text-white py-3 px-6 rounded-lg font-semibold hover:bg-gray-700 mb-4">
          Create an account
        </button>
        {/* קישור להתחברות */}
        <p className="text-center text-sm text-gray-600">
          Already have an account?{' '}
          <a href="/login" className="font-semibold text-gray-800 hover:underline">
            Log in
          </a>
        </p>
      </div>
    </div>
  );
}

export default LandingPage;
