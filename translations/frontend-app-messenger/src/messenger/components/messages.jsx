import { defineMessages } from '@edx/frontend-platform/i18n';

const messages = defineMessages({
  // Buttons
  'messenger.button.send': {
    id: 'messenger.button.send',
    defaultMessage: 'Send',
    description: 'Label for the send button in messenger',
  },
  'messenger.button.close': {
    id: 'messenger.button.close',
    defaultMessage: 'Close',
    description: 'Label for the close button in messenger',
  },
  'messenger.button.cancel': {
    id: 'messenger.button.cancel',
    defaultMessage: 'Cancel',
    description: 'Label for the cancel button in messenger',
  },
  'messenger.button.reply': {
    id: 'messenger.button.reply',
    defaultMessage: 'Reply',
    description: 'Label for the reply button in messenger',
  },
  'messenger.button.newMessage': {
    id: 'messenger.button.newMessage',
    defaultMessage: 'New Message',
    description: 'Label for starting a new message',
  },

  // Placeholders
  'messenger.placeholder.typeMessage': {
    id: 'messenger.placeholder.typeMessage',
    defaultMessage: 'Type your message...',
    description: 'Placeholder text for typing a message',
  },
  'messenger.placeholder.enterMessage': {
    id: 'messenger.placeholder.enterMessage',
    defaultMessage: 'Enter Message ...',
    description: 'Placeholder text for entering a message',
  },
  'messenger.placeholder.username': {
    id: 'messenger.placeholder.username',
    defaultMessage: 'username',
    description: 'Placeholder for username',
  },
  'messenger.placeholder.searchUsers': {
    id: 'messenger.placeholder.searchUsers',
    defaultMessage: 'Search Users',
    description: 'Placeholder for user search input',
  },
  'messenger.placeholder.select': {
    id: 'messenger.placeholder.select',
    defaultMessage: 'Select',
    description: 'Placeholder for select dropdown',
  },

  // Labels
  'messenger.label.inbox': {
    id: 'messenger.label.inbox',
    defaultMessage: 'Inbox',
    description: 'Label for the inbox section',
  },
  'messenger.label.message': {
    id: 'messenger.label.message',
    defaultMessage: 'Message',
    description: 'Label for message section',
  },
  'messenger.label.newMessage': {
    id: 'messenger.label.newMessage',
    defaultMessage: 'New Message',
    description: 'Label for new message section',
  },
  'messenger.label.users': {
    id: 'messenger.label.users',
    defaultMessage: 'Users',
    description: 'Label for users section',
  },

  // Success messages
  'messenger.success.sendMessage': {
    id: 'messenger.success.sendMessage',
    defaultMessage: 'Message has been sent.',
    description: 'Success message when a message is sent',
  },
  'messenger.success.sendMessages': {
    id: 'messenger.success.sendMessages',
    defaultMessage: 'Message(s) have been sent.',
    description: 'Success message when multiple messages are sent',
  },

  // Error messages
  'messenger.error.sendMessage': {
    id: 'messenger.error.sendMessage',
    defaultMessage: 'Error in sending message. Please try again!',
    description: 'Error when message sending fails',
  },
  'messenger.error.sendMessages': {
    id: 'messenger.error.sendMessages',
    defaultMessage: 'Error in sending messages. Please try again!',
    description: 'Error when multiple message sending fails',
  },
  'messenger.error.readMessages': {
    id: 'messenger.error.readMessages',
    defaultMessage: 'Error in marking messages read.',
    description: 'Error when marking messages as read',
  },
  'messenger.error.loadConversation': {
    id: 'messenger.error.loadConversation',
    defaultMessage: 'Unable to load conversations.',
    description: 'Error when loading conversations fails',
  },
  'messenger.error.userConversation': {
    id: 'messenger.error.userConversation',
    defaultMessage: 'Unable to load conversation of user:',
    description: 'Error when loading user conversation fails',
  },
  'messenger.error.userSearch': {
    id: 'messenger.error.userSearch',
    defaultMessage: 'Unable to search users.',
    description: 'Error when searching users fails',
  },

  // Extra
  'messenger.inbox.noConversation': {
    id: 'messenger.inbox.noConversation',
    defaultMessage: 'No conversation found!',
    description: 'Message shown when the inbox is empty',
  },
});

export default messages;
