export function displayEventTitle(title = '') {
  return String(title).replace(/^(?:\[DEMO\]\s*)+/i, '');
}

export function displayText(value = '') {
  return String(value).replace(/^(?:\[DEMO DATA\]\s*)+/i, '');
}

export function displayCategoryName(value = '') {
  return String(value).replace(/^(?:\[DEMO\]\s*)+/i, '');
}

export function displayBookingReference(value = '') {
  return String(value).replace(/^DEMO-/i, '');
}

export function isInternalDemoText(value = '') {
  return /^(?:\[DEMO(?: DATA)?\])/i.test(String(value));
}

export function isInternalDemoNotification(notification = {}) {
  return isInternalDemoText(notification.title) && isInternalDemoText(notification.message);
}
