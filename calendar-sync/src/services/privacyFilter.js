/**
 * Privacy Filter
 *
 * Transforms customer data for safe syncing to external calendars.
 * Only exposes: First Name + Last 2 digits of phone number
 *
 * Example:
 *   Input:  { customerName: "John Smith", customerPhone: "(555) 123-4567" }
 *   Output: "John 67"
 */

/**
 * Extract first name from full name
 * @param {string} fullName - Full customer name
 * @returns {string} First name only
 */
function extractFirstName(fullName) {
  if (!fullName || typeof fullName !== 'string') {
    return 'Customer';
  }
  const trimmed = fullName.trim();
  const firstName = trimmed.split(/\s+/)[0];
  return firstName || 'Customer';
}

/**
 * Extract last 2 digits from phone number
 * @param {string} phone - Phone number in any format
 * @returns {string} Last 2 digits, or "XX" if unavailable
 */
function extractLastTwoDigits(phone) {
  if (!phone || typeof phone !== 'string') {
    return 'XX';
  }
  // Remove all non-digit characters
  const digits = phone.replace(/\D/g, '');
  if (digits.length < 2) {
    return 'XX';
  }
  return digits.slice(-2);
}

/**
 * Create privacy-filtered display title
 * @param {Object} event - Event with customer info
 * @param {string} event.customerName - Full customer name
 * @param {string} event.customerPhone - Customer phone number
 * @param {string} [event.service] - Optional service type
 * @returns {string} Privacy-filtered title
 */
function createFilteredTitle(event) {
  const firstName = extractFirstName(event.customerName);
  const lastTwo = extractLastTwoDigits(event.customerPhone);

  let title = `${firstName} ${lastTwo}`;

  // Optionally append service type if provided
  if (event.service) {
    title += ` - ${event.service}`;
  }

  return title;
}

/**
 * Transform a full event into a privacy-filtered version for Google Calendar
 * @param {Object} event - Full event data from Frontdesk
 * @returns {Object} Privacy-filtered event for Google Calendar
 */
function filterEventForGoogle(event) {
  const title = createFilteredTitle(event);

  return {
    summary: title,
    start: {
      dateTime: event.startTime,
      timeZone: event.timeZone || 'America/New_York',
    },
    end: {
      dateTime: event.endTime,
      timeZone: event.timeZone || 'America/New_York',
    },
    description: event.notes ? `Notes: ${event.notes}` : '',
    // Store original ID in extended properties for reverse lookup
    extendedProperties: {
      private: {
        syncSource: 'frontdesk',
        originalId: event.id || '',
        lastTwo: extractLastTwoDigits(event.customerPhone),
      },
    },
  };
}

/**
 * Parse a privacy-filtered title back to components
 * @param {string} title - Privacy-filtered title (e.g., "John 67 - Consultation")
 * @returns {Object} Parsed components
 */
function parseFilteredTitle(title) {
  if (!title) {
    return { firstName: null, lastTwo: null, service: null };
  }

  // Pattern: "FirstName XX" or "FirstName XX - Service"
  const match = title.match(/^(\w+)\s+(\d{2})(?:\s*-\s*(.+))?$/);

  if (match) {
    return {
      firstName: match[1],
      lastTwo: match[2],
      service: match[3] || null,
    };
  }

  // Couldn't parse - return title as-is
  return {
    firstName: null,
    lastTwo: null,
    service: null,
    rawTitle: title,
  };
}

module.exports = {
  extractFirstName,
  extractLastTwoDigits,
  createFilteredTitle,
  filterEventForGoogle,
  parseFilteredTitle,
};
