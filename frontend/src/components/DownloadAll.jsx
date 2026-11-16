import { useState } from 'react';
import api from '../api';

const DownloadAll = ({ bookingId, bookingReference }) => {
  const [downloading, setDownloading] = useState(false);

  const handleDownloadAll = async () => {
    try {
      setDownloading(true);
      const response = await api.get(
        `/tickets/booking/${bookingId}/download-all/`,
        { responseType: 'blob' }
      );
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `booking_${bookingReference}_tickets.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download tickets: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="download-all-section">
      <button
        className="btn btn-download-all"
        onClick={handleDownloadAll}
        disabled={downloading}
      >
        {downloading ? 'Downloading All Tickets...' : 'Download All Tickets (PDF)'}
      </button>
    </div>
  );
};

export default DownloadAll;
