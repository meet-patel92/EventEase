import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { displayBookingReference } from '../utils/eventTitle';

function PaymentHistory() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadPayments = useCallback(async () => {
    try {
      const response = await api.get('/payments/');
      const results = Array.isArray(response.data) ? response.data : response.data?.results;
      if (!Array.isArray(results)) throw new Error('The payment service returned an unexpected response.');
      setPayments(results);
      setError('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.response?.data?.error || requestError.message || 'Could not load payment history.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Load only records allowed by the backend role-scoped payment queryset.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadPayments();
  }, [loadPayments]);

  return (
    <section className="page-container">
      <div className="page-header"><h1>Payment history</h1><Link to="/bookings" className="btn btn-secondary">Bookings</Link></div>
      {loading && <p className="loading" role="status">Loading payments…</p>}
      {error && <div className="error" role="alert">{error}<button className="btn btn-primary" onClick={() => { setLoading(true); loadPayments(); }}>Retry</button></div>}
      {!loading && !error && payments.length === 0 && <p className="empty-state">No payment attempts are available yet.</p>}
      {!loading && payments.length > 0 && (
        <div className="table-scroll"><table className="data-table">
          <thead><tr><th>Booking</th><th>Amount</th><th>Payment status</th><th>Method</th><th>Date</th></tr></thead>
          <tbody>{payments.map((payment) => (
            <tr key={payment.id}>
              <td>{displayBookingReference(payment.booking_reference || `#${payment.booking}`)}</td>
              <td>{payment.currency || 'INR'} {payment.amount}</td>
              <td><span className={`status-badge ${payment.status.toLowerCase()}`}>{payment.status}</span></td>
              <td>{payment.payment_method || payment.provider || '—'}</td>
              <td>{new Date(payment.created_at).toLocaleString()}</td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
    </section>
  );
}

export default PaymentHistory;

