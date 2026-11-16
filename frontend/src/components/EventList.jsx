import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import EventPoster from './EventPoster';
import { displayCategoryName, displayEventTitle } from '../utils/eventTitle';
import { ArrowRight, Music2, Palette, Users, Utensils, Search, CalendarCheck, CalendarDays, CreditCard, PartyPopper, Sparkles } from 'lucide-react';

function getEvents(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  throw new Error('The events service returned an unexpected response.');
}

function EventList() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [cityInput, setCityInput] = useState('');
  const [dateInput, setDateInput] = useState('');
  const [filters, setFilters] = useState({});
  const loadEvents = useCallback(async () => {
    try {
      const response = await api.get('/events/', { params: filters });
      setEvents(getEvents(response.data));
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Could not load events.');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const applyFilters = (event) => {
    event.preventDefault();
    setLoading(true);
    setFilters({
      search: searchInput.trim() || undefined,
      city: cityInput.trim() || undefined,
      event_date: dateInput || undefined,
    });
  };

  const exploreCategory = (category) => {
    setSearchInput(category);
    setFilters({ search: category });
    setLoading(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const featuredEvents = events.slice(0, 3);

  useEffect(() => {
    // The async request updates state when the network response arrives.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadEvents();
  }, [loadEvents]);

  return (
    <div className="home-page">
      <section className="home-hero" aria-labelledby="events-heading">
        <div className="hero-content">
          <span className="hero-kicker"><Sparkles size={15} />Make room for a good time</span>
          <h1 id="events-heading" aria-label="Find your next event">Your next great<br /><em>memory</em> starts here.</h1>
          <p>Find local experiences, live moments, and the people you’ll remember them with.</p>
          <a className="btn btn-primary hero-cta" href="#upcoming-events">Explore events <ArrowRight size={17} /></a>
          <span className="hero-note"><span className="hero-note-dot" />Thoughtfully picked events near you</span>
        </div>
        <div className="hero-art" aria-hidden="true">{events[0] && <EventPoster className="hero-event-poster" src={events[0].poster} alt="" />}<div className="hero-art-tag"><CalendarCheck size={17} /><span><strong>Make a plan</strong><small>Something to look forward to</small></span></div></div>
      </section>

      <div className="home-content">
        <section className="category-section" aria-labelledby="category-heading">
          <div className="home-section-heading"><div><p className="eyebrow">Find your kind of fun</p><h2 id="category-heading">Explore by interest</h2></div><span>Pick a mood, find a moment.</span></div>
          <div className="category-grid">
            <button className="category-card category-music" onClick={() => exploreCategory('music')}><span className="category-icon"><Music2 size={21} /></span><strong>Music &amp; live</strong><small>Shows, concerts, and more</small></button>
            <button className="category-card category-arts" onClick={() => exploreCategory('art')}><span className="category-icon"><Palette size={21} /></span><strong>Arts &amp; culture</strong><small>Ideas worth experiencing</small></button>
            <button className="category-card category-community" onClick={() => exploreCategory('community')}><span className="category-icon"><Users size={21} /></span><strong>Community</strong><small>Meet, learn, connect</small></button>
            <button className="category-card category-food" onClick={() => exploreCategory('food')}><span className="category-icon"><Utensils size={21} /></span><strong>Food &amp; festivals</strong><small>Good tastes, good times</small></button>
          </div>
        </section>

        <section className="events-section" id="upcoming-events" aria-labelledby="upcoming-heading">
          <div className="home-section-heading"><div><p className="eyebrow">Get out there</p><h2 id="upcoming-heading">Upcoming events</h2></div><span>Real events. Ready when you are.</span></div>

      <form className="event-filter-form" onSubmit={applyFilters}>
        <label className="event-search-label"><span>Search</span><span className="event-search-input"><Search size={17} /><input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Event or venue" /></span></label>
        <label>City<input value={cityInput} onChange={(event) => setCityInput(event.target.value)} placeholder="Any city" /></label>
        <label>Date<input type="date" value={dateInput} onChange={(event) => setDateInput(event.target.value)} /></label>
        <button className="btn btn-primary">Search events</button>
      </form>

      {loading && <p className="loading" role="status">Loading events…</p>}

      {!loading && error && (
        <div className="error events-error" role="alert">
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => {
            setLoading(true);
            setError('');
            loadEvents();
          }}>Retry</button>
        </div>
      )}

      {!loading && !error && events.length === 0 && (
        <p className="empty-state" role="status">No events are available right now. Please check back soon.</p>
      )}

      {!loading && !error && events.length > 0 && (
        <>
        <div className="featured-grid" aria-label="Featured upcoming events">
          {featuredEvents.map((event, index) => <article className={`featured-event featured-event-${index + 1}`} key={`featured-${event.id}`}>
            <EventPoster className="featured-poster" src={event.poster} alt={`${displayEventTitle(event.title)} poster`} />
            <div className="featured-overlay"><span>{displayCategoryName(event.category_name || 'Featured event')}</span><strong>{displayEventTitle(event.title)}</strong><p><CalendarDays size={15} />{event.event_date}{event.city ? ` · ${event.city}` : ''}</p><Link to={`/events/${event.id}`} aria-label={`View ${displayEventTitle(event.title)}`}>Discover <ArrowRight size={15} /></Link></div>
          </article>)}
        </div>
        <div className="events-grid">
          {events.map((event) => (
            <article className="event-card" key={event.id}>
              <EventPoster className="event-poster" src={event.poster} alt={`${displayEventTitle(event.title)} poster`} />
              <div className="event-card-content">
                <p className="event-date">{event.event_date}</p>
                <h2><Link to={`/events/${event.id}`}>{displayEventTitle(event.title)}</Link></h2>
                <p>{event.venue}{event.city ? ` · ${event.city}` : ''}</p>
                {event.ticket_price != null && <p className="event-price">₹{event.ticket_price}</p>}
                <p className="event-availability">{event.available_tickets} tickets available</p>
                <Link to={`/events/${event.id}`} className="btn btn-primary event-view-link">View event</Link>
              </div>
            </article>
          ))}
        </div>
        </>
      )}
        </section>

        <section className="how-section" aria-labelledby="how-heading"><div className="home-section-heading"><div><p className="eyebrow">Simple from start to finish</p><h2 id="how-heading">A good plan in three steps</h2></div></div><div className="how-grid"><article><span><Search size={21} /></span><h3>Find your thing</h3><p>Browse upcoming experiences and discover something new.</p></article><article><span><CreditCard size={21} /></span><h3>Book with ease</h3><p>Choose your tickets and keep your booking details together.</p></article><article><span><PartyPopper size={21} /></span><h3>Show up &amp; enjoy</h3><p>Bring your ticket, meet your people, and make the moment yours.</p></article></div></section>
      </div>
    </div>
  );
}

export default EventList;

