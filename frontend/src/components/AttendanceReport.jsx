import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../api';
import { displayEventTitle } from '../utils/eventTitle';

function AttendanceReport() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    api.get(`/events/${id}/attendance/`).then(({ data }) => { if (active) setReport(data); })
      .catch((requestError) => { if (active) setError(requestError.response?.data?.detail || requestError.response?.data?.error || 'Could not load attendance report.'); });
    return () => { active = false; };
  }, [id]);
  return <section className="page-container management-page">
    <header className="page-header"><div><p className="eyebrow">Organizer workspace</p><h1>Attendance report</h1>{report && <p>{displayEventTitle(report.event_title)}</p>}</div><Link className="btn btn-secondary" to="/organizer/events">Back to my events</Link></header>
    {error && <p className="error" role="alert">{error}</p>}
    {!report && !error && <p className="loading" role="status">Loading attendance…</p>}
    {report && <div className="attendance-grid" aria-label="Attendance summary">
      <article><span>Total paid tickets</span><strong>{report.total_paid_tickets}</strong></article>
      <article><span>Checked-in tickets</span><strong>{report.checked_in_tickets}</strong></article>
      <article><span>Remaining tickets</span><strong>{report.remaining_tickets}</strong></article>
      <article><span>Attendance</span><strong>{report.attendance_percentage}%</strong></article>
    </div>}
  </section>;
}
export default AttendanceReport;
