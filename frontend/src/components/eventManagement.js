export function getListItems(data, resourceName) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  throw new Error(`The ${resourceName} service returned an unexpected response.`);
}

export function getApiError(error, fallback) {
  const data = error.response?.data;
  if (typeof data === 'string') return data;
  if (data?.detail) return data.detail;
  if (data?.error) return data.error;

  const messages = [];
  const collect = (value, path = '') => {
    if (Array.isArray(value)) value.forEach((item) => collect(item, path));
    else if (value && typeof value === 'object') {
      Object.entries(value).forEach(([key, nested]) => collect(nested, key));
    } else if (value) messages.push(path ? `${path}: ${value}` : String(value));
  };
  collect(data);
  return messages.join(' ') || error.message || fallback;
}

export async function getAllEvents() {
  const { default: api } = await import('../api');
  const events = [];
  let next = '/events/';
  while (next) {
    const response = await api.get(next);
    events.push(...getListItems(response.data, 'events'));
    next = response.data.next || null;
  }
  return events;
}

export function statusClass(status) {
  return `event-status-badge ${String(status || '').toLowerCase()}`;
}

