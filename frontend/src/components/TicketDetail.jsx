import { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import api from '../api';
import EventPoster from './EventPoster';
import { displayBookingReference, displayEventTitle } from '../utils/eventTitle';

const TicketDetail = () => {
  const { id } = useParams();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const navigate = useNavigate();

  const fetchTicket = useCallback(async () => {
    try {
      const response = await api.get(`/tickets/${id}/`);
      setTicket(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load ticket');
    } finally {
      setLoading(false);
    }
  }, [id]);

  const handleDownloadPdf = async () => {
    if (!ticket) return;
    try {
      setDownloading(true);
      const response = await api.get(`/tickets/${ticket.id}/download/`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `ticket_${ticket.ticket_number}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download PDF: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDownloading(false);
    }
  };

  useEffect(() => {
    // Fetch the selected ticket after its detail route mounts.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchTicket();
  }, [fetchTicket]);

  if (loading) {
    return (
      <div className="page-container">
        <h1>Ticket Details</h1>
        <div className="loading">Loading ticket...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <h1>Ticket Details</h1>
        <div className="error">{error}</div>
        <button className="btn btn-primary" onClick={() => navigate('/tickets')}>
          Back to Tickets
        </button>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="page-container">
        <h1>Ticket Details</h1>
        <div className="empty-state">
          <p>Ticket not found.</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/tickets')}>
          Back to Tickets
        </button>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Ticket Details</h1>
        <Link to="/tickets" className="btn btn-secondary">
          ← Back to Tickets
        </Link>
      </div>

      <div className="ticket-detail">
        <div className="ticket-info">
          <EventPoster className="ticket-event-image ticket-detail-image" src={ticket.event_poster} alt={`${displayEventTitle(ticket.event_title)} poster`} />
          <h2>{displayEventTitle(ticket.event_title)}</h2>
          <div className="info-grid">
            <div className="info-row">
              <span className="label">Ticket number (reference):</span>
              <span className="value">#{ticket.ticket_number}</span>
            </div>
            <div className="info-row">
              <span className="label">Booking Ref:</span>
              <span className="value">{displayBookingReference(ticket.booking_reference)}</span>
            </div>
            <div className="info-row">
              <span className="label">Event Date:</span>
              <span className="value">{ticket.event_date}</span>
            </div>
            <div className="info-row">
              <span className="label">Time:</span>
              <span className="value">{ticket.start_time} - {ticket.end_time}</span>
            </div>
            <div className="info-row">
              <span className="label">Venue:</span>
              <span className="value">{ticket.venue}</span>
            </div>
            <div className="info-row">
              <span className="label">City:</span>
              <span className="value">{ticket.city}</span>
            </div>
            <div className="info-row">
              <span className="label">Booking ID:</span>
              <span className="value">{ticket.booking_id ?? ticket.booking}</span>
            </div>
            <div className="info-row">
              <span className="label">Booking reference:</span>
              <span className="value">{ticket.booking_reference || '—'}</span>
            </div>
            <div className="info-row">
              <span className="label">Ticket quantity:</span>
              <span className="value">{ticket.booking_quantity ?? 1}</span>
            </div>
            <div className="info-row">
              <span className="label">Total price:</span>
              <span className="value">₹{ticket.booking_total_amount ?? '—'}</span>
            </div>
            <div className="info-row">
              <span className="label">Booking status:</span>
              <span className={`status-badge ${(ticket.booking_status || 'unknown').toLowerCase()}`}>
                {ticket.booking_status || 'Unknown'}
              </span>
            </div>
            <div className="info-row">
              <span className="label">Customer:</span>
              <span className="value">{ticket.customer_email}</span>
            </div>
            <div className="info-row">
              <span className="label">Status:</span>
              <span className={`status-badge ${ticket.status.toLowerCase()}`}>
                {ticket.status}
              </span>
            </div>
            <div className="info-row">
              <span className="label">Issued:</span>
              <span className="value">{ticket.issued_at}</span>
            </div>
          </div>
        </div>

        <div className="ticket-actions">
          {ticket.qr_code_url && (
            <div className="qr-section">
              <img src={ticket.qr_code_url} alt="QR Code" className="qr-code" />
              <p className="qr-label">Scan to verify</p>
            </div>
          )}
          {ticket.ticket_token && (
            <div className="ticket-manual-code" aria-label="Check-in code">
              <strong>Check-in code</strong>
              <code>{ticket.ticket_token}</code>
              <p>Scanner manual entry ke liye yahi code use karein. Ticket number aur booking reference alag references hain.</p>
            </div>
          )}
          <button
            className="btn btn-download"
            onClick={handleDownloadPdf}
            disabled={downloading}
          >
            {downloading ? 'Downloading...' : 'Download PDF'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TicketDetail;

