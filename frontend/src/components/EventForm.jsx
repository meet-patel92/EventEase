import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { getApiError, getListItems } from './eventManagement';
import EventPoster from './EventPoster';
import { displayCategoryName, displayEventTitle, displayText } from '../utils/eventTitle';

const emptyEvent = {
  title: '', description: '', category: '', venue: '', address: '', city: '',
  event_date: '', start_time: '', end_time: '', registration_deadline: '',
  ticket_price: '0.00', total_tickets: '1', available_tickets: '1',
};

function dateTimeLocal(value) {
  return value ? String(value).slice(0, 16) : '';
}

function EventForm() {
  const { id } = useParams();
  const editing = Boolean(id);
  const navigate = useNavigate();
  const [values, setValues] = useState(emptyEvent);
  const [categories, setCategories] = useState([]);
  const [categoryLoading, setCategoryLoading] = useState(true);
  const [categoryError, setCategoryError] = useState('');
  const [categoryRetry, setCategoryRetry] = useState(0);
  const [currentCategoryName, setCurrentCategoryName] = useState('');
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [posterPreview, setPosterPreview] = useState('');

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        api.get('/events/categories/')
          .then((categoryResponse) => {
            if (!active) return;
            const rows = getListItems(categoryResponse.data, 'categories');
            setCategories(rows);
            setCategoryError('');
          })
          .catch((requestError) => {
            if (active) {
              setCategories([]);
              setCategoryError(getApiError(requestError, 'Could not load event categories.'));
            }
          })
          .finally(() => { if (active) setCategoryLoading(false); });

        if (editing) {
          const eventResponse = await api.get(`/events/${id}/`);
          if (!active) return;
          const event = eventResponse.data;
          setCurrentCategoryName(displayCategoryName(event.category_name || ''));
          setValues({
            ...emptyEvent,
            ...Object.fromEntries(Object.keys(emptyEvent).map((key) => [
              key,
              key === 'title' ? displayEventTitle(event[key])
                : key === 'description' || key === 'address' ? displayText(event[key])
                  : event[key] ?? '',
            ])),
            category: event.category ?? '',
            registration_deadline: dateTimeLocal(event.registration_deadline),
            ticket_price: String(event.ticket_price ?? '0.00'),
            total_tickets: String(event.total_tickets ?? 1),
            available_tickets: String(event.available_tickets ?? 1),
          });
          setPosterPreview(event.poster || '');
        }
      } catch (requestError) {
        if (active) setError(getApiError(requestError, 'Could not load event details.'));
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => { active = false; };
  }, [editing, id, categoryRetry]);

  const update = (event) => setValues((current) => ({ ...current, [event.target.name]: event.target.value }));
  const selectPoster = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) { setError('Please choose an image file.'); event.target.value = ''; return; }
    if (file.size > 5 * 1024 * 1024) { setError('Poster image size must be 5 MB or less.'); event.target.value = ''; return; }
    setError('');
    setPosterPreview(URL.createObjectURL(file));
  };

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setNotice('');
    const formData = new FormData(event.currentTarget);
    if (!formData.get('category')) formData.delete('category');
    if (!formData.get('registration_deadline')) formData.delete('registration_deadline');
    if (!formData.get('poster')?.size) formData.delete('poster');
    try {
      const response = editing
        ? await api.patch(`/events/${id}/`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
        : await api.post('/events/', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      if (editing) {
        setNotice('Event details saved.');
        navigate('/organizer/events', { state: { notice: 'Event details saved.' } });
      } else {
        navigate('/organizer/events', { state: { notice: `${displayEventTitle(response.data.title)} was submitted for approval.` } });
      }
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not save the event. Check the fields and try again.'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <section className="page-container"><p className="loading" role="status">Loading event form…</p></section>;

  return (
    <section className="page-container management-page">
      <header className="page-header"><div><p className="eyebrow">Organizer workspace</p><h1>{editing ? 'Edit Event' : 'Create Event'}</h1></div><Link className="btn btn-secondary" to="/organizer/events">Back to my events</Link></header>
      <p>New events are submitted with PENDING status for administrator review.</p>
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="success-message" role="status">{notice}</p>}
      {categoryError && <div className="error" role="alert"><p>{categoryError}</p><button className="btn btn-secondary" type="button" onClick={() => { setCategoryError(''); setCategoryLoading(true); setCategoryRetry((current) => current + 1); }}>Retry categories</button></div>}
      {!categoryLoading && !categoryError && !categories.length && <p className="management-help" role="status">No event categories are available. You can continue without a category.</p>}
      <form className="management-form" onSubmit={submit} encType="multipart/form-data">
        <div className="management-form-grid">
          <label>Event title<input name="title" value={values.title} onChange={update} required maxLength="200" /></label>
          <label>Category<select name="category" value={values.category} onChange={update} disabled={categoryLoading || Boolean(categoryError)}><option value="">{categoryLoading ? 'Loading categories…' : 'No category'}</option>{values.category && !categories.some((category) => String(category.id) === String(values.category)) && <option value={values.category}>{currentCategoryName || 'Current category'}</option>}{categories.map((category) => <option value={category.id} key={category.id}>{displayCategoryName(category.name)}</option>)}</select></label>
          <label className="management-form-wide">Description<textarea name="description" value={values.description} onChange={update} required rows="4" /></label>
          <label>Venue<input name="venue" value={values.venue} onChange={update} required maxLength="200" /></label>
          <label>City<input name="city" value={values.city} onChange={update} required maxLength="100" /></label>
          <label className="management-form-wide">Address<input name="address" value={values.address} onChange={update} /></label>
          <label>Event date<input type="date" name="event_date" value={values.event_date} onChange={update} required /></label>
          <label>Registration deadline<input type="datetime-local" name="registration_deadline" value={values.registration_deadline} onChange={update} /></label>
          <label>Start time<input type="time" name="start_time" value={values.start_time} onChange={update} required /></label>
          <label>End time<input type="time" name="end_time" value={values.end_time} onChange={update} required /></label>
          <label>Ticket price<input type="number" name="ticket_price" min="0" step="0.01" value={values.ticket_price} onChange={update} required /></label>
          <label>Total tickets<input type="number" name="total_tickets" min="1" step="1" value={values.total_tickets} onChange={update} required /></label>
          <label>Available tickets<input type="number" name="available_tickets" min="0" step="1" max={values.total_tickets || undefined} value={values.available_tickets} onChange={update} required /></label>
          <label>Poster image<input type="file" name="poster" accept="image/jpeg,image/png,image/webp,image/gif" onChange={selectPoster} />{editing && <small>Choose a new image to replace the current poster. Leave blank to keep it.</small>}<small>JPEG, PNG, WebP or GIF · Maximum 5 MB</small></label>
        </div>
        <div className="poster-preview"><h2>Poster preview</h2><EventPoster className="poster-preview-image" src={posterPreview} alt="Event poster preview" /></div>
        <div className="management-actions"><button className="btn btn-primary" disabled={saving || categoryLoading}>{saving ? 'Saving…' : editing ? 'Save changes' : 'Submit event'}</button><Link className="btn btn-secondary" to="/organizer/events">Cancel</Link></div>
      </form>
    </section>
  );
}

export default EventForm;
