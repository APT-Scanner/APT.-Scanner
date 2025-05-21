import styles from '../styles/LoadingSpinner.module.css';
import { Loader } from 'lucide-react';

export const LoadingSpinner = () => (
    <div className={styles.loadingContainer}>
      <div className={styles.spinner}>
        <Loader size={40} className={styles.spinnerIcon} />
        <p>Loading...</p>
      </div>
    </div>
  );