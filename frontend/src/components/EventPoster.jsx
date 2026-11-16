import { useState } from 'react';

function EventPoster({ src, alt = 'Event poster', className = '' }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) return <div className={`${className} event-poster-placeholder`} role="img" aria-label="Event poster unavailable"><span>EventEase</span><strong>Make it memorable</strong></div>;
  return <img className={className} src={src} alt={alt} onError={() => setFailed(true)} />;
}

export default EventPoster;
