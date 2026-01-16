import PropTypes from 'prop-types';

import { PluginSlot } from '@openedx/frontend-plugin-framework/dist';

import { getConfig } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';

export const UserMentionPluginSlot = ({ editor }) => (
  <PluginSlot
    id="org.openedx.frontend.discussions.user_mention_plugin.v1"
    idAliases={['user_mention_plugin']}
    pluginProps={{
      editor,
      authClient: getAuthenticatedHttpClient,
      getConfig,
    }}
  />
);

UserMentionPluginSlot.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  editor: PropTypes.any.isRequired,
};
