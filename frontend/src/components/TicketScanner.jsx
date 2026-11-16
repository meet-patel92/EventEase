import { useCallback, useEffect, useRef, useState } from 'react';
import api from '../api';
import { useSearchParams } from 'react-router-dom';
import { displayEventTitle } from '../utils/eventTitle';

function TicketScanner() {
  const [events, setEvents] = useState([]);
  const [eventId, setEventId] = useState('');
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [cameraError, setCameraError] = useState('');
  const [stream, setStream] = useState(null);
  const [eventTicketCount, setEventTicketCount] = useState(null);
  const [searchParams] = useSearchParams();
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const detectorRef = useRef(null);
  const scannerControlsRef = useRef(null);
  const mountedRef = useRef(false);
  const role = (() => { try { return JSON.parse(localStorage.getItem('user') || 'null')?.role; } catch { return null; } })();

  useEffect(() => {
    let active = true;
    const endpoint = role === 'ORGANIZER' ? '/events/my-events/' : '/events/';
    api.get(endpoint).then((response) => {
      const rows = Array.isArray(response.data) ? response.data : response.data?.results || [];
      if (active) {
        const eligible = role === 'ORGANIZER' ? rows.filter((row) => row.status === 'APPROVED') : rows;
        setEvents(eligible);
        const selectedId = searchParams.get('event');
        if (selectedId && eligible.some((row) => String(row.id) === selectedId)) setEventId(selectedId);
      }
    }).catch((requestError) => {
      if (active) setError(requestError.response?.data?.detail || 'Could not load events for ticket verification.');
    });
    return () => { active = false; };
  }, [role, searchParams]);

  useEffect(() => {
    let active = true;
    if (role === 'ORGANIZER' && eventId) {
      api.get(`/events/${eventId}/attendance/`).then(({ data }) => {
        if (active) setEventTicketCount({ eventId, count: data.total_paid_tickets });
      }).catch(() => {
        if (active) setEventTicketCount({ eventId, count: null });
      });
    }
    return () => { active = false; };
  }, [eventId, role]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      scannerControlsRef.current?.stop();
      streamRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (videoRef.current && stream && typeof stream.getTracks === 'function') videoRef.current.srcObject = stream;
    return () => stream?.getTracks?.().forEach((track) => track.stop());
  }, [stream]);

  const stopCamera = useCallback(() => {
    scannerControlsRef.current?.stop();
    scannerControlsRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    detectorRef.current = null;
    setStream(null);
  }, []);

  useEffect(() => {
    if (!stream || !videoRef.current || !detectorRef.current) return undefined;
    let scanning = true;
    const detector = detectorRef.current;
    const scan = async () => {
      if (!scanning || !videoRef.current || videoRef.current.readyState < 2) return;
      try {
        const codes = await detector.detect(videoRef.current);
        if (codes.length && codes[0].rawValue) {
          setToken(codes[0].rawValue);
          scanning = false;
        }
      } catch {
        setCameraError('Camera scan failed. Enter the check-in code manually.');
      }
    };
    const timer = window.setInterval(scan, 700);
    return () => { scanning = false; window.clearInterval(timer); };
  }, [stream]);

  const startCamera = async () => {
    setCameraError('');
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError('Camera access is not available here. Enter the check-in code manually.');
      return;
    }
    try {
      detectorRef.current = 'BarcodeDetector' in window
        ? new window.BarcodeDetector({ formats: ['qr_code'] })
        : null;
    } catch {
      detectorRef.current = null;
    }
    if (!detectorRef.current) {
      try {
        const { BrowserQRCodeReader } = await import('@zxing/browser');
        const reader = new BrowserQRCodeReader();
        setStream(true);
        await new Promise((resolve) => window.requestAnimationFrame(resolve));
        let decoded = false;
        const controls = await reader.decodeFromVideoDevice(undefined, videoRef.current, (result, scanError, activeControls) => {
          if (result && mountedRef.current) {
            decoded = true;
            setToken(result.getText());
            activeControls.stop();
            scannerControlsRef.current = null;
            setStream(null);
          } else if (scanError && scanError.name !== 'NotFoundException') {
            setCameraError('QR scan failed. Enter the check-in code manually.');
          }
        });
        if (!mountedRef.current) {
          controls.stop();
          return;
        }
        if (!decoded) scannerControlsRef.current = controls;
      } catch {
        setStream(null);
        setCameraError('Camera access was denied or unavailable. Enter the check-in code manually.');
      }
      return;
    }
    try {
      const cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      if (!mountedRef.current) {
        cameraStream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = cameraStream;
      setStream(cameraStream);
    } catch {
      detectorRef.current = null;
      setCameraError('Camera access was denied or unavailable. Enter the check-in code manually.');
    }
  };

  const verify = async (event) => {
    event.preventDefault();
    setError('');
    setResult(null);
    try {
      const response = await api.post('/tickets/verify/', {
        ticket_token: token.trim(),
        event_id: Number(eventId),
      });
      setResult(response.data);
      setToken('');
      stopCamera();
    } catch (requestError) {
      setError(requestError.response?.data?.error || requestError.response?.data?.detail || 'Ticket could not be verified.');
    }
  };

  return (
    <section className="page-container scanner-page">
      <div className="page-header"><div><p className="eyebrow">Event staff</p><h1>Ticket check-in</h1></div></div>
      <p>Choose the event, scan the QR code, or enter the customer ticket ka clearly labelled Check-in code. Ticket number ya booking reference enter na karein.</p>
      <label className="scanner-event-label">Event
        <select value={eventId} onChange={(change) => setEventId(change.target.value)} required>
          <option value="">Select an event</option>
          {events.map((event) => <option key={event.id} value={event.id}>{displayEventTitle(event.title)} — {event.event_date}</option>)}
        </select>
      </label>
      <div className={`scanner-video-wrap${stream ? '' : ' scanner-video-hidden'}`}><video ref={videoRef} autoPlay playsInline muted />{stream && <button className="btn btn-secondary" onClick={stopCamera}>Stop camera</button>}</div>
      {!stream && <button className="btn btn-secondary" onClick={startCamera}>Start camera scanner</button>}
      {cameraError && <p className="error" role="alert">{cameraError}</p>}
      {role === 'ORGANIZER' && eventTicketCount?.eventId === eventId && eventTicketCount.count === 0 && <p className="scanner-empty-tickets" role="status">No paid tickets have been issued for this event yet. Tickets become available after payment is successfully verified.</p>}
      {role === 'ORGANIZER' && eventTicketCount?.eventId === eventId && eventTicketCount.count > 0 && <p className="scanner-ticket-count" role="status">{eventTicketCount.count} paid ticket{eventTicketCount.count === 1 ? '' : 's'} available for check-in.</p>}
      <form className="scanner-form" onSubmit={verify}>
        <label htmlFor="ticket-token">Check-in code</label>
        <input id="ticket-token" value={token} onChange={(change) => setToken(change.target.value)} required autoComplete="off" />
        <button className="btn btn-primary" disabled={!eventId || !token.trim()}>Verify and check in</button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      {result && <div className="scanner-result" role="status"><h2>Ticket checked in</h2><p>{displayEventTitle(result.event_title)}</p><p>{result.event_date} · {result.venue}</p><p>Ticket #{result.ticket_number} · {result.ticket_status}</p></div>}
    </section>
  );
}

export default TicketScanner;
