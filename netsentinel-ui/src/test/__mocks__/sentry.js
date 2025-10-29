// Mock for sentry utilities
module.exports = {
  initSentry: jest.fn(),
  setUserContext: jest.fn(),
  clearUserContext: jest.fn(),
  captureException: jest.fn(),
  captureMessage: jest.fn(),
  addBreadcrumb: jest.fn(),
};
