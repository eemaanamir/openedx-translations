import { ensureConfig, getConfig } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient as getHttpClient } from '@edx/frontend-platform/auth';
import { camelCaseObject, snakeCaseObject } from './utils';

ensureConfig(['LMS_BASE_URL']);

function processAndThrowError(error, errorDataProcessor) {
  const processedError = Object.create(error);
  if (error.response && error.response.data && typeof error.response.data === 'object') {
    processedError.processedData = errorDataProcessor(error.response.data);
    throw processedError;
  } else {
    throw error;
  }
}

export const getBaseURL = () => `${getConfig().LMS_BASE_URL}/messenger/api/v0`;

/**
 * Create a single message
 */
export async function createMessageService(payload) {
  const processedParams = snakeCaseObject(payload);
  const { data } = await getHttpClient()
    .post(`${getBaseURL()}/message/`, processedParams)
    .catch((error) => processAndThrowError(error, camelCaseObject));
  return camelCaseObject(data);
}

/**
 * Create messages for multiple users
 */
export async function createGroupMessagesService(payload) {
  const processedParams = snakeCaseObject(payload);
  const { data } = await getHttpClient()
    .post(`${getBaseURL()}/bulk_message/`, processedParams)
    .catch((error) => processAndThrowError(error, camelCaseObject));
  return camelCaseObject(data);
}

/**
 * Update inbox unread count
 */
export async function updateUnreadCountService(inboxId) {
  const { data } = await getHttpClient()
    .patch(`${getBaseURL()}/inbox/${inboxId}/`, snakeCaseObject({ unread_count: 0 }))
    .catch((error) => processAndThrowError(error, camelCaseObject));
  return camelCaseObject(data);
}

/**
 * Fetch inbox list with pagination & search
 */
export async function fetchInboxListService(page, search = '') {
  const { data } = await getHttpClient()
    .get(`${getBaseURL()}/inbox/?page=${page}&search=${search}`)
    .catch((error) => processAndThrowError(error, camelCaseObject));
  return camelCaseObject(data);
}

/**
 * Fetch conversation/messages for a user
 */
export async function fetchSelectedInboxMessagesService(page, withUser) {
  const { data } = await getHttpClient()
    .get(`${getBaseURL()}/conversation/?page=${page}&with_user=${withUser}`)
    .catch((error) => processAndThrowError(error, camelCaseObject));
  return camelCaseObject(data);
}

/**
 * Search users
 */
export async function fetchUsersService(query) {
  const { data } = await getHttpClient()
    .get(`${getBaseURL()}/user/?search=${query}`)
    .catch((error) => processAndThrowError(error, camelCaseObject));
  return camelCaseObject(data);
}

/**
 * Get account info (for username, profile image, etc.)
 */

function processAccountData(data) {
  const processedData = camelCaseObject(data);
  return {
    ...processedData,
    socialLinks: Array.isArray(processedData.socialLinks) ? processedData.socialLinks : [],
    languageProficiencies: Array.isArray(processedData.languageProficiencies)
      ? processedData.languageProficiencies : [],
    name: processedData.name || null,
    bio: processedData.bio || null,
    country: processedData.country || null,
    levelOfEducation: processedData.levelOfEducation || null,
    profileImage: processedData.profileImage || {},
    yearOfBirth: processedData.yearOfBirth || null,
  };
}

export async function getAccountService(username) {
  const { data } = await getHttpClient().get(`${getConfig().LMS_BASE_URL}/api/user/v1/accounts/${username}`);

  return processAccountData(data);
}
