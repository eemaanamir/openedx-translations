import React, { useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { useDispatch, useSelector } from 'react-redux';
import Multiselect from 'multiselect-react-dropdown';
import messages from './messages';
import { searchUsers, clearSearchResults } from '../store/slices/userSlice';
import { createGroupMessages } from '../store/slices/inboxSlice';
import { addMessageToList } from '../store/slices/messagesSlice';

const NewMessageModal = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const [groupMessage, setGroupMessage] = useState('');
  const [selectedUsers, setSelectedUsers] = useState([]);

  const { searchResults } = useSelector((state) => state.user);
  const { selectedUser } = useSelector((state) => state.inbox);
  const { currentUser } = useSelector((state) => state.user);

  const handleSearch = (query) => {
    if (query) {
      dispatch(searchUsers(query));
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();

    if (!groupMessage.trim() || selectedUsers.length === 0) {
      return;
    }

    const receivers = selectedUsers.map((user) => user.id);

    dispatch(createGroupMessages({ receivers, message: groupMessage })).then(() => {
      // Check if conversation is opened with any of the selected users
      const isConversationOpened = selectedUsers.some(
        (user) => user.username === selectedUser,
      );

      if (isConversationOpened) {
        dispatch(
          addMessageToList({
            sender: currentUser.username,
            sender_img: currentUser.profileImage || '',
            created: 'now',
            message: groupMessage,
          }),
        );
      }

      // Reset form
      setGroupMessage('');
      setSelectedUsers([]);
      dispatch(clearSearchResults());

      // Close modal
      const modalElement = document.getElementById('messageModalCenter');
      if (modalElement) {
        window.jQuery(modalElement).modal('hide');
      }
    });
  };

  return (
    <div>
      <div
        className="modal fade modal-update"
        id="messageModalCenter"
        tabIndex="-1"
        role="dialog"
        aria-labelledby="messageModalCenterTitle"
        aria-hidden="true"
      >
        <div className="modal-dialog modal-dialog-centered modal-lg" role="document">
          <div className="modal-content">
            <form onSubmit={handleSubmit}>
              <div className="modal-header">
                <h5 className="modal-title" id="messageModalLongTitle">
                  {intl.formatMessage(messages['messenger.label.newMessage'])}
                </h5>
                <button type="button" className="close" data-dismiss="modal" aria-label="Close">
                  <span aria-hidden="true">&times;</span>
                </button>
              </div>
              <div className="modal-body">
                {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
                <label>
                  {intl.formatMessage(messages['messenger.label.users'])}
                </label>
                <Multiselect
                  options={searchResults}
                  displayValue="username"
                  onSearch={handleSearch}
                  selectedValues={selectedUsers}
                  onSelect={setSelectedUsers}
                  onRemove={setSelectedUsers}
                  placeholder={intl.formatMessage(messages['messenger.placeholder.select'])}
                />
                <div className="form-group">
                  <label htmlFor="group-message">
                    {intl.formatMessage(messages['messenger.label.message'])}
                  </label>
                  <textarea
                    className="form-control"
                    id="group-message"
                    placeholder={intl.formatMessage(messages['messenger.placeholder.enterMessage'])}
                    required
                    onChange={(e) => setGroupMessage(e.target.value)}
                    value={groupMessage}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" data-dismiss="modal">
                  {intl.formatMessage(messages['messenger.button.close'])}
                </button>
                <button type="submit" className="btn btn-primary">
                  {intl.formatMessage(messages['messenger.button.send'])}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewMessageModal;
