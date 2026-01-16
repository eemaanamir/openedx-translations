import React, { useEffect, useCallback, useRef } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { useDispatch, useSelector } from 'react-redux';
import Spinner from '../assets/spinner';
import messages from './messages';
import {
  fetchMessages,
  createMessage as createMessageAction,
  incrementPageNumber,
  setIsReplying,
  setCurrentMessage,
  clearCurrentMessage,
} from '../store/slices/messagesSlice';
import { updateLastMessage, updateUnreadCount } from '../store/slices/inboxSlice';

const Conversation = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const observer = useRef();
  const textareaRef = useRef(null);

  const { selectedUser, list: inboxList } = useSelector((state) => state.inbox);
  const {
    list: messagesList,
    loading,
    hasMore,
    pageNumber,
    isReplying,
    currentMessage,
  } = useSelector((state) => state.messages);
  const { currentUser } = useSelector((state) => state.user);

  // Fetch messages when user is selected
  useEffect(() => {
    if (selectedUser) {
      dispatch(fetchMessages({ pageNumber: 1, username: selectedUser }));
    }
  }, [selectedUser, dispatch]);

  // Handle pagination
  useEffect(() => {
    if (selectedUser && pageNumber > 1) {
      dispatch(fetchMessages({ pageNumber, username: selectedUser }));
    }
  }, [pageNumber, selectedUser, dispatch]);

  // Mark messages as read after 3 seconds
  useEffect(() => {
    if (!selectedUser || !inboxList.length) { return () => {}; }

    const currentInbox = inboxList.find(
      (inbox) => inbox.withUser === selectedUser,
    );

    if (currentInbox && currentInbox.unreadCount) {
      const timer = setTimeout(() => {
        dispatch(updateUnreadCount(currentInbox.id));
      }, 3000);

      return () => clearTimeout(timer);
    }
    return () => {};
  }, [selectedUser, inboxList, dispatch]);

  // eslint-disable-next-line consistent-return
  const lastMessageRef = useCallback(
    (node) => {
      if (loading) { return; }
      if (observer.current) { observer.current.disconnect(); }

      observer.current = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && hasMore) {
          dispatch(incrementPageNumber());
        }
      });

      if (node) { observer.current.observe(node); }
    },
    [loading, hasMore, dispatch],
  );

  const handleSendMessage = () => {
    if (!currentMessage.trim()) { return; }

    dispatch(
      createMessageAction({
        receiver: selectedUser,
        message: currentMessage,
      }),
    ).then(() => {
      dispatch(updateLastMessage({ username: selectedUser, message: currentMessage }));
    });
  };

  const handleInputChange = (e) => {
    dispatch(setCurrentMessage(e.target.value));
    e.target.style.height = '5px';
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  const handleCancelReply = () => {
    dispatch(clearCurrentMessage());
  };

  const handleReplyClick = () => {
    dispatch(setIsReplying(true));
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>
          {intl.formatMessage(messages['messenger.label.inbox'])} / {selectedUser}&nbsp;
        </h2>
      </div>
      <div className="chat">
        {isReplying && (
          <div className="chat-row">
            {currentUser.hasProfileImage ? (
              <img src={currentUser.profileImage} alt={currentUser.name} />
            ) : (
              <span className="img-placeholder" style={{ background: '#a7f9e0' }}>
                {currentUser.profileName}
              </span>
            )}
            <div className="chat-detail">
              <div className="new-message">
                <textarea
                  ref={textareaRef}
                  className="new-message-input"
                  value={currentMessage}
                  placeholder={intl.formatMessage(messages['messenger.placeholder.typeMessage'])}
                  onChange={handleInputChange}
                  // eslint-disable-next-line jsx-a11y/no-autofocus
                  autoFocus
                />
                <div className="btn-box">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleSendMessage}
                    disabled={!currentMessage.trim().length}
                  >
                    {intl.formatMessage(messages['messenger.button.send'])}
                  </button>
                  <button
                    type="button"
                    className="btn btn-default"
                    onClick={handleCancelReply}
                  >
                    {intl.formatMessage(messages['messenger.button.close'])}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {messagesList.length > 0 && !loading && !isReplying && (
          <div className="chat-reply">
            <button
              type="button"
              className="btn btn-default"
              onClick={handleReplyClick}
            >
              {intl.formatMessage(messages['messenger.button.reply'])}
            </button>
          </div>
        )}

        {messagesList
          && !loading
          && messagesList.map((message, index) => {
            const isLastItem = messagesList.length === index + 1;
            const hasProfileImage = message.senderImg?.indexOf('default_50') === -1;
            const profileName = `${message.sender[0]}${
              message.sender.split(' ')[1]
                ? message.sender.split(' ')[1][0]
                : message.sender[1]
            }`;

            return (
              <div
                className="chat-row"
                key={message.id || index}
                ref={isLastItem ? lastMessageRef : null}
              >
                {hasProfileImage ? (
                  <img src={message.senderImg} alt={message.sender} />
                ) : (
                  <span className="img-placeholder" style={{ background: '#a7f9e0' }}>
                    {profileName}
                  </span>
                )}
                <div className="chat-detail">
                  <span className="msg-sender">{message.sender}</span>
                  <span className="chat-time">{message.created}</span>
                  <pre>{message.message}</pre>
                </div>
              </div>
            );
          })}

        {loading && <Spinner />}
      </div>
    </div>
  );
};

export default Conversation;
