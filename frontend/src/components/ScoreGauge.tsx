import React, { useEffect, useState } from 'react';
import './ScoreGauge.css';

interface ScoreGaugeProps {
  score: number;
  label: string;
  size?: 'sm' | 'md' | 'lg';
  showPercentage?: boolean;
  animate?: boolean;
}

const SIZE_CONFIG = {
  sm: { size: 80, strokeWidth: 6, fontSize: 18, labelSize: 10 },
  md: { size: 120, strokeWidth: 8, fontSize: 28, labelSize: 12 },
  lg: { size: 160, strokeWidth: 10, fontSize: 36, labelSize: 14 },
};

function getScoreColor(score: number): string {
  if (score >= 90) return 'var(--score-excellent)';
  if (score >= 50) return 'var(--score-average)';
  return 'var(--score-poor)';
}

function getScoreLabel(score: number): string {
  if (score >= 90) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 50) return 'Average';
  return 'Poor';
}

export const ScoreGauge: React.FC<ScoreGaugeProps> = ({
  score,
  label,
  size = 'md',
  showPercentage = true,
  animate = true,
}) => {
  const [animatedScore, setAnimatedScore] = useState(animate ? 0 : score);
  const config = SIZE_CONFIG[size];
  
  const radius = (config.size - config.strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const progress = (animatedScore / 100) * circumference;
  const dashOffset = circumference - progress;
  
  const scoreColor = getScoreColor(score);

  useEffect(() => {
    if (!animate) {
      setAnimatedScore(score);
      return;
    }

    // Animate from 0 to score over 600ms
    const duration = 600;
    const startTime = performance.now();
    const startScore = 0;
    const endScore = score;

    const animateFrame = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Ease-out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const currentScore = startScore + (endScore - startScore) * easeOut;
      
      setAnimatedScore(Math.round(currentScore));

      if (progress < 1) {
        requestAnimationFrame(animateFrame);
      }
    };

    requestAnimationFrame(animateFrame);
  }, [score, animate]);

  return (
    <div className="score-gauge" style={{ width: config.size, height: config.size }}>
      <svg
        width={config.size}
        height={config.size}
        viewBox={`0 0 ${config.size} ${config.size}`}
        className="score-gauge-svg"
      >
        {/* Background track */}
        <circle
          cx={config.size / 2}
          cy={config.size / 2}
          r={radius}
          fill="none"
          stroke="var(--border-subtle)"
          strokeWidth={config.strokeWidth}
          className="score-gauge-track"
        />
        
        {/* Progress arc */}
        <circle
          cx={config.size / 2}
          cy={config.size / 2}
          r={radius}
          fill="none"
          stroke={scoreColor}
          strokeWidth={config.strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          className="score-gauge-progress"
          transform={`rotate(-90 ${config.size / 2} ${config.size / 2})`}
        />
      </svg>
      
      {/* Score display */}
      <div className="score-gauge-content">
        <span 
          className="score-gauge-value" 
          style={{ fontSize: config.fontSize, color: scoreColor }}
        >
          {animatedScore}
          {showPercentage && <span className="score-gauge-percent">%</span>}
        </span>
        <span 
          className="score-gauge-label" 
          style={{ fontSize: config.labelSize }}
        >
          {label}
        </span>
      </div>
    </div>
  );
};

export default ScoreGauge;
