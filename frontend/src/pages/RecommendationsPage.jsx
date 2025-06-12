import React from 'react';
import styles from '../styles/RecommendationsPage.module.css';
import { ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import glilotImage from '../assets/neighbourhoods/Gililot.jpg';
import orotImage from '../assets/neighbourhoods/Orot.jpeg';
import oldNorthImage from '../assets/neighbourhoods/New North - North Side.jpg';

const sampleRecommendations = [
  { id: 1, name: 'Glilot', city: 'Tel Aviv Yaffo', image: glilotImage, match: 97 },
  { id: 2, name: 'Orot', city: 'Tel Aviv Yaffo', image: orotImage, match: 93 },
  { id: 3, name: 'Old North - North Side', city: 'Tel Aviv Yaffo', image: oldNorthImage, match: 90 }
];

const RecommendationsPage = () => {
  const navigate = useNavigate();

  const handleBack = () => navigate(-1);

  return (
    <div className={styles.pageContainer}>
      <button className={styles.backButton} onClick={handleBack} aria-label="Go Back">
        <ArrowLeft size={24} color="#371b34" />
      </button>

      <h1 className={styles.mainTitle}>
        Your<br />Recommendations<br />Are Ready!
      </h1>

      <p className={styles.description}>
        Based on your questionnaire, we've found the top neighborhoods that suit your lifestyle preferences:
      </p>

      <section className={styles.listContainer}>
        {sampleRecommendations.map((rec) => (
          <div
            key={rec.id}
            className={styles.listItem}
            style={{ backgroundImage: `url(${rec.image})` }}
            onClick={() => navigate(`/apartment-swipe`)}
          >
            <div className={styles.itemOverlay}>
              <span className={styles.itemName}>{rec.name}, {rec.city}</span>
              <span className={styles.itemMatch}>{rec.match}% Match</span>
            </div>
          </div>
        ))}
      </section>

      <p className={styles.hintText}>
        Click on one of them to start swiping
        <br />
        <span className={styles.manualLink} onClick={() => navigate('/apartment-swipe')}>or choose manually</span>
      </p>
    </div>
  );
};

export default RecommendationsPage;