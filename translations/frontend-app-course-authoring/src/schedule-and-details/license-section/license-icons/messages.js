import { defineMessages } from '@edx/frontend-platform/i18n';

const messages = defineMessages({
  allRightReservedLabel: {
    id: 'course-authoring.schedule-section.license.all-right-reserved.label',
    defaultMessage: 'All rights reserved',
  },
  creativeCommonsReservedLabel: {
    id: 'course-authoring.schedule-section.license.creative-commons.label',
    defaultMessage: 'Some rights reserved',
  },
  creativeCommonsSAReservedLabel: {
    id: 'course-authoring.schedule-section.creativeCommons.shareAlike.text',
    defaultMessage: 'CC-by-sa 4.0',
    description: 'License text shown when using share-alike Creative Commons license types.',
  },
});

export default messages;
