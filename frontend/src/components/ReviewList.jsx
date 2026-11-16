import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { isInternalDemoText } from '../utils/eventTitle';

function ReviewList() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadReviews = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/reviews/');
      const rows = Array.isArray(response.data) ? response.data : response.data?.results;
      if (!Array.isArray(rows)) throw new Error('The reviews service returned an unexpected response.');
      setReviews(rows.filter((review) => !isInternalDemoText(review.comment)));
      setError('');
    } catch (requestError) {
      const data = requestError.response?.data;
      setError(data?.detail || requestError.message || 'Could not load reviews.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Reviews are read asynchronously after the route mounts.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadReviews();
  }, [loadReviews]);

  return (
    <section className="page-container" aria-labelledby="reviews-page-heading">
      <div className="page-header">
        <div><p className="eyebrow">Attendee feedback</p><h1 id="reviews-page-heading">Event reviews</h1></div>
        <button className="btn btn-secondary" onClick={loadReviews} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
      {loading && <p className="loading" role="status">Loading reviews…</p>}
      {!loading && error && (
        <div className="error" role="alert">
          <p>{error}</p>
          <button className="btn btn-primary" onClick={loadReviews}>Retry</button>
        </div>
      )}
      {!loading && !error && reviews.length === 0 && (
        <p className="empty-state" role="status">No event reviews have been submitted yet.</p>
      )}
      {!loading && !error && reviews.length > 0 && (
        <div className="review-list">
          {reviews.map((review) => (
            <article className="review-card" key={review.id}>
              <div className="review-card-heading">
                <strong>{review.user_email || 'Event attendee'}</strong>
                <span aria-label={`${review.rating} out of 5 stars`}>{'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}</span>
              </div>
              {review.comment && <p>{review.comment}</p>}
              <footer>
                <Link to={`/events/${review.event}`}>View event</Link>
                <time dateTime={review.created_at}>{new Date(review.created_at).toLocaleDateString()}</time>
              </footer>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default ReviewList;

