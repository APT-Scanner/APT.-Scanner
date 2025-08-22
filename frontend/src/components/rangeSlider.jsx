import React, { useRef, useEffect, useCallback } from 'react';
import styles from '../styles/FilterPage.module.css';

const RangeSlider = ({
    min,
    max,
    step,
    valueMin,
    valueMax,
    onChangeMin,
    onChangeMax,
    labels = [],
}) => {
    const sliderRef = useRef(null);
    const draggingRef = useRef(null);

    const handleMouseDown = (handleType) => (e) => {
        draggingRef.current = handleType;
        if (e.target instanceof HTMLElement) {
            e.target.classList.add(styles.active);
        }
    };

    const handleMouseUp = useCallback(() => {
        if (draggingRef.current) {
            document.querySelectorAll(`.${styles.rangeHandle}.${styles.active}`).forEach(handle => {
                handle.classList.remove(styles.active);
            });
            draggingRef.current = null;
        }
    }, []);

    const handleMouseMove = useCallback((e) => {
        if (!draggingRef.current || !sliderRef.current) return;

        if (e.type === 'touchmove') e.preventDefault();

        const rect = sliderRef.current.getBoundingClientRect();
        let offsetX = e.clientX - rect.left;

        if (e.touches?.length) {
            offsetX = e.touches[0].clientX - rect.left;
        }

        let percentage = Math.max(0, Math.min(100, (offsetX / rect.width) * 100));
        let newValue = min + (percentage / 100) * (max - min);
        newValue = Math.round(newValue / step) * step;

        if (draggingRef.current === 'min') {
            onChangeMin(Math.max(min, Math.min(newValue, valueMax)));
        } else {
            onChangeMax(Math.min(max, Math.max(newValue, valueMin)));
        }
    }, [min, max, step, valueMin, valueMax, onChangeMin, onChangeMax]);

    useEffect(() => {
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('touchmove', handleMouseMove, { passive: false });
        document.addEventListener('mouseup', handleMouseUp);
        document.addEventListener('touchend', handleMouseUp);
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('touchmove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.removeEventListener('touchend', handleMouseUp);
        };
    }, [handleMouseMove, handleMouseUp]);

    const leftPercent = ((valueMin - min) / (max - min)) * 100;
    const widthPercent = ((valueMax - valueMin) / (max - min)) * 100;

    return (
        <div>
            <div className={styles.rangeInputsContainer}>
                        <input 
                            type="number" 
                            className={styles.rangeInput} 
                            value={valueMin}
                            onChange={(e) => onChangeMin(Math.max(min, Math.min(parseInt(e.target.value) || min, valueMax)))}
                            placeholder="Min"
                            step="100"
                        />
                        <input 
                            type="number" 
                            className={styles.rangeInput} 
                            value={valueMax}
                            onChange={(e) => onChangeMax(Math.min(max, Math.max(parseInt(e.target.value) || max, valueMin)))}
                            placeholder="Max"
                            step="100"
                />
            </div>
            <div className={styles.rangeSlider} ref={sliderRef}>
                <div className={styles.rangeTrack} style={{ left: `${leftPercent}%`, width: `${widthPercent}%` }}></div>
                {labels.map((label, idx) => (
                    <div
                        key={idx}
                        className={styles.rangeDot}
                        style={{ left: `${((label - min) / (max - min)) * 100}%` }}
                    ></div>
                ))}
                <div
                    className={styles.rangeHandle}
                    style={{ left: `${leftPercent}%` }}
                    onMouseDown={handleMouseDown('min')}
                    onTouchStart={handleMouseDown('min')}
                ></div>
                <div
                    className={styles.rangeHandle}
                    style={{ left: `${leftPercent + widthPercent}%` }}
                    onMouseDown={handleMouseDown('max')}
                    onTouchStart={handleMouseDown('max')}
                ></div>
                <div className={styles.rangeLabels}>
                    {labels.map((label, idx) => (
                        <div
                            key={idx}
                            className={styles.rangeLabels}
                            style={{ left: `${((label - min) / (max - min)) * 100}%` }}
                        >
                            {label}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default RangeSlider;
