import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { isInternalDemoText } from '../utils/eventTitle';

function errorMessage(error) {
  const data = error.response?.data;
  if (data && typeof data === 'object') return Object.values(data).flat().filter(Boolean).join(' ');
  return data || error.message || 'Could not save your review.';
}

function ReviewSection({ eventId }) {
  const user = useMemo(() => {
    try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; }
  }, []);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');
  const [rating, setRating] = useState('5');
  const [comment, setComment] = useState('');
  const [saving, setSaving] = useState(false);

  const ownReview = reviews.find((review) => review.user === user?.id);
  const publicReviews = reviews.filter((review) => !isInternalDemoText(review.comment));

  const loadReviews = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/reviews/', { params: { event: eventId } });
      const rows = Array.isArray(response.data) ? response.data : response.data?.results;
      if (!Array.isArray(rows)) throw new Error('The reviews service returned an unexpected response.');
      setReviews(rows);
      const mine = rows.find((review) => review.user === user?.id);
      if (mine) {
        setRating(String(mine.rating));
        setComment(isInternalDemoText(mine.comment) ? '' : mine.comment || '');
      }
      setLoadError('');
    } catch (error) {
      setLoadError(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [eventId, user?.id]);

  useEffect(() => {
    // The review request is asynchronous and updates state when it completes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadReviews();
  }, [loadReviews]);

  const saveReview = async (event) => {
    event.preventDefault();
    setFormError('');
    setSuccess('');
    const numericRating = Number(rating);
    if (!Number.isInteger(numericRating) || numericRating < 1 || numericRating > 5) {
      setFormError('Choose a rating from 1 to 5.');
      return;
    }

    setSaving(true);
    try {
      const payload = { event: Number(eventId), rating: numericRating, comment };
      const response = ownReview
        ? await api.patch(`/reviews/${ownReview.id}/`, payload)
        : await api.post('/reviews/', payload);
      setReviews((current) => ownReview
        ? current.map((review) => review.id === response.data.id ? response.data : review)
        : [response.data, ...current]);
      setSuccess('Your review was saved.');
    } catch (error) {
      setFormError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="review-section" aria-labelledby="reviews-heading">
      <div className="section-heading-row">
        <div><p className="eyebrow">Attendee feedback</p><h2 id="reviews-heading">Reviews</h2></div>
        <span className="review-count">{publicReviews.length} {publicReviews.length === 1 ? 'review' : 'reviews'}</span>
      </div>

      {loading && <p className="loading" role="status">Loading reviews…</p>}
      {!loading && loadError && (
        <div className="error" role="alert">
          <p>{loadError}</p>
          <button className="btn btn-secondary" onClick={loadReviews}>Retry reviews</button>
        </div>
      )}
      {!loading && !loadError && publicReviews.length === 0 && (
        <p className="empty-state" role="status">No reviews yet. Be the first to share your experience.</p>
      )}
      {!loading && !loadError && publicReviews.length > 0 && (
        <div className="review-list">
          {publicReviews.map((review) => (
            <article className="review-card" key={review.id}>
              <div className="review-card-heading">
                <strong>{review.user_email || 'Event attendee'}</strong>
                <span aria-label={`${review.rating} out of 5 stars`}>{'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}</span>
              </div>
              {review.comment && <p>{review.comment}</p>}
              {review.user === user?.id && <small>Your review</small>}
            </article>
          ))}
        </div>
      )}

      {user?.role === 'CUSTOMER' ? (
        <form className="review-form" onSubmit={saveReview}>
          <h3>{ownReview ? 'Update your review' : 'Share your review'}</h3>
          <label htmlFor={`review-rating-${eventId}`}>Rating</label>
          <select
            id={`review-rating-${eventId}`}
            value={rating}
            onChange={(change) => setRating(change.target.value)}
            required
          >
            {[5, 4, 3, 2, 1].map((value) => <option key={value} value={value}>{value} {value === 1 ? 'star' : 'stars'}</option>)}
          </select>
          <label htmlFor={`review-comment-${eventId}`}>Comment</label>
          <textarea
            id={`review-comment-${eventId}`}
            rows="3"
            maxLength="2000"
            value={comment}
            onChange={(change) => setComment(change.target.value)}
            placeholder="What did you think of this event?"
          />
          {formError && <p className="error" role="alert">{formError}</p>}
          {success && <p className="success-message" role="status">{success}</p>}
          <button className="btn btn-primary" type="submit" disabled={saving}>
            {saving ? 'Saving review…' : ownReview ? 'Update review' : 'Submit review'}
          </button>
        </form>
      ) : !user ? (
        <p className="review-signin"><Link to="/login">Sign in as a customer</Link> to leave a review.</p>
      ) : null}
    </section>
  );
}

export default ReviewSection;


