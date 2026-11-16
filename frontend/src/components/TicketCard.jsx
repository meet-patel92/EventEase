import { Link } from 'react-router-dom';
import EventPoster from './EventPoster';
import { displayBookingReference, displayEventTitle } from '../utils/eventTitle';

const TicketCard = ({ ticket, onDownloadPdf }) => {
  return (
    <div className="ticket-card">
      <EventPoster className="ticket-event-image" src={ticket.event_poster} alt={`${displayEventTitle(ticket.event_title)} poster`} />
      <div className="ticket-header">
        <span className="ticket-number">Ticket number (reference): {ticket.ticket_number}</span>
        <span className={`status-badge ${ticket.status.toLowerCase()}`}>
          {ticket.status}
        </span>
      </div>
      
      <div className="ticket-info">
        <div className="info-row">
          <span className="label">Event:</span>
          <span className="value">{displayEventTitle(ticket.event_title)}</span>
        </div>
        <div className="info-row">
          <span className="label">Date:</span>
          <span className="value">{ticket.event_date}</span>
        </div>
        <div className="info-row">
          <span className="label">Time:</span>
          <span className="value">
            {ticket.start_time} - {ticket.end_time}
          </span>
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
          <span className="value">{displayBookingReference(ticket.booking_reference || '—')}</span>
        </div>
        <div className="info-row">
          <span className="label">Quantity:</span>
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
      </div>

      <div className="ticket-actions">
        <Link to={`/tickets/${ticket.id}`} className="btn btn-primary">
          View Details
        </Link>
        <button
          className="btn btn-download"
          onClick={(e) => {
            e.stopPropagation();
            onDownloadPdf(ticket.id, ticket.ticket_number);
          }}
        >
          Download PDF
        </button>
      </div>
    </div>
  );
};

export default TicketCard;

