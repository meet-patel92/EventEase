import { useCallback, useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import api from '../api';
import TicketCard from './TicketCard';

const TicketList = () => {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const location = useLocation();
  const currentUser = (() => {
    try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; }
  })();
  const isCustomer = currentUser?.role === 'CUSTOMER';
  const ticketListEndpoint = isCustomer ? '/tickets/my-tickets/' : '/tickets/';

  const fetchTickets = useCallback(async () => {
    try {
      const allTickets = [];
      const seenPages = new Set();
      let pageNumber = 1;

      while (pageNumber && !seenPages.has(pageNumber)) {
        seenPages.add(pageNumber);
        const response = await api.get(ticketListEndpoint, {
          params: pageNumber === 1 ? undefined : { page: pageNumber },
        });
        const data = response.data;

        if (Array.isArray(data)) {
          allTickets.push(...data);
          break;
        }
        if (!data || !Array.isArray(data.results)) {
          throw new Error('The tickets service returned an unexpected response.');
        }

        allTickets.push(...data.results);
        if (!data.next) break;

        const apiOrigin = new URL(api.defaults.baseURL).origin;
        const nextUrl = new URL(data.next, api.defaults.baseURL);
        const nextPage = Number(nextUrl.searchParams.get('page'));
        if (nextUrl.origin !== apiOrigin || !Number.isInteger(nextPage) || nextPage < 1) {
          throw new Error('The tickets service returned an invalid pagination link.');
        }
        pageNumber = nextPage;
      }

      setTickets(allTickets);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.error || err.message || 'Failed to load tickets.');
    } finally {
      setLoading(false);
    }
  }, [ticketListEndpoint]);

  const handleDownloadPdf = async (ticketId, ticketNumber) => {
    try {
      const response = await api.get(`/tickets/${ticketId}/download/`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `ticket_${ticketNumber}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download PDF: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDownloadBookingPdf = async (bookingId, bookingReference) => {
    try {
      const response = await api.get(`/tickets/booking/${bookingId}/download-all/`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `booking_${bookingReference}_tickets.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download booking tickets: ' + (err.response?.data?.detail || err.message));
    }
  };

  useEffect(() => {
    // Fetch the user's current tickets after the protected page mounts.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchTickets();
  }, [fetchTickets]);

  if (loading) {
    return (
      <div className="page-container">
        <h1>{isCustomer ? 'My Tickets' : 'Tickets'}</h1>
        <div className="loading">Loading tickets...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <h1>{isCustomer ? 'My Tickets' : 'Tickets'}</h1>
        <div className="error" role="alert">{error}</div>
        <button className="btn btn-primary" onClick={() => {
          setLoading(true);
          setError(null);
          fetchTickets();
        }}>
          Try Again
        </button>
      </div>
    );
  }

  if (tickets.length === 0) {
    return (
      <div className="page-container empty">
        <h1>{isCustomer ? 'My Tickets' : 'Tickets'}</h1>
        <div className="empty-state">
          <p>{isCustomer ? "You haven't booked any tickets yet." : 'No tickets are available for this account.'}</p>
        </div>
        {isCustomer && <Link to="/" className="btn btn-primary">Explore Events</Link>}
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{isCustomer ? 'My Tickets' : 'Tickets'}</h1>
        <p>You have {tickets.length} {tickets.length === 1 ? 'ticket' : 'tickets'}</p>
      </div>

      {location.state?.bookingReference && (
        <div className="booking-confirmation" role="status">
          <strong>Booking {location.state.bookingStatus?.toLowerCase() || 'confirmed'}.</strong>
          <span>Reference: {location.state.bookingReference}</span>
        </div>
      )}

      <div className="ticket-booking-downloads" aria-label="Download all tickets by booking">
        {[...new Map(tickets.map((ticket) => [ticket.booking_id ?? ticket.booking, ticket])).values()].map((ticket) => (
          <button
            key={ticket.booking_id ?? ticket.booking}
            type="button"
            className="btn btn-secondary"
            onClick={() => handleDownloadBookingPdf(ticket.booking_id ?? ticket.booking, ticket.booking_reference || ticket.booking_id || ticket.booking)}
          >
            Download all tickets for {ticket.booking_reference || `booking #${ticket.booking_id ?? ticket.booking}`}
          </button>
        ))}
      </div>
      
      <div className="ticket-grid">
        {tickets.map((ticket) => (
          <TicketCard
            key={ticket.id}
            ticket={ticket}
            onDownloadPdf={handleDownloadPdf}
          />
        ))}
      </div>
    </div>
  );
};

export default TicketList;
