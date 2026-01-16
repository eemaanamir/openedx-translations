/* eslint-disable jsx-a11y/click-events-have-key-events,
jsx-a11y/no-static-element-interactions,
jsx-a11y/no-noninteractive-element-interactions */
import React, { useEffect, useCallback, useRef } from 'react';
import PropTypes from 'prop-types';
import { useIntl } from '@edx/frontend-platform/i18n';
import { useDispatch, useSelector } from 'react-redux';
import Spinner from '../assets/spinner';
import messages from './messages';
import {
  fetchInboxList,
  setSelectedUser,
  setSearchQuery,
  incrementPageNumber,
  resetPageNumber,
} from '../store/slices/inboxSlice';
import { resetMessages } from '../store/slices/messagesSlice';

const Inbox = ({ isDrawerShown, setDrawerShown }) => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const observer = useRef();

  const {
    list: inboxList,
    selectedUser,
    loading,
    hasMore,
    pageNumber,
    searchQuery,
  } = useSelector((state) => state.inbox);

  // Fetch initial inbox list
  useEffect(() => {
    dispatch(fetchInboxList({ pageNumber: 1, searchQuery: '' }));
  }, [dispatch]);

  // Handle search with debounce
  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    if (searchQuery !== '') {
      const delayDebounceFetch = setTimeout(() => {
        dispatch(resetPageNumber());
        dispatch(fetchInboxList({ pageNumber: 1, searchQuery }));
      }, 500);

      return () => clearTimeout(delayDebounceFetch);
    } if (searchQuery === '' && pageNumber === 1) {
      dispatch(fetchInboxList({ pageNumber: 1, searchQuery: '' }));
    }
    return () => {};
  }, [searchQuery, dispatch]);

  // Handle pagination
  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    if (pageNumber > 1) {
      dispatch(fetchInboxList({ pageNumber, searchQuery }));
    }
  }, [pageNumber, dispatch]);

  // Intersection Observer for infinite scroll
  const lastInboxRef = useCallback(
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

  const handleInboxClick = (username) => {
    dispatch(setSelectedUser(username));
    dispatch(resetMessages());
    setDrawerShown(!isDrawerShown);
  };

  const handleSearchChange = (e) => {
    dispatch(setSearchQuery(e.target.value));
  };

  const handleClearSearch = () => {
    dispatch(setSearchQuery(''));
  };

  const renderDate = (dateStr) => {
    const date = new Date(dateStr).toDateString();
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();

    if (today === date) { return 'Today'; }
    if (yesterday === date) { return 'Yesterday'; }
    return dateStr;
  };

  return (
    <div className="chat-sidebar">
      <div className="chat-sidebar-header">
        <div className="btn-box">
          <strong className="text">
            {intl.formatMessage(messages['messenger.label.inbox'])}
          </strong>
          <button
            type="button"
            className="btn btn-primary btn-lg start-new-msg-btn"
            data-toggle="modal"
            data-target="#messageModalCenter"
          >
            <span className="icon-plus">+</span>
            {intl.formatMessage(messages['messenger.button.newMessage'])}
          </button>
        </div>
        <div className="search-box">
          <span className="fa fa-search" />
          <input
            type="text"
            value={searchQuery}
            onChange={handleSearchChange}
            className="search-field"
            placeholder={intl.formatMessage(messages['messenger.placeholder.searchUsers'])}
          />
          {searchQuery && (
            <span className="fa fa-times-circle" onClick={handleClearSearch} />
          )}
        </div>
        <span
          className="fa fa-cog"
          onClick={() => setDrawerShown(!isDrawerShown)}
        />
      </div>
      <ul className="inbox-list">
        {loading && pageNumber === 1 && <Spinner />}
        {inboxList.length === 0 && !loading ? (
          <span>{intl.formatMessage(messages['messenger.inbox.noConversation'])}</span>
        ) : (
          inboxList.map((inbox, index) => {
            const username = inbox.withUser;

            // Skip if no username
            if (!username) { return null; }

            const isLastItem = inboxList.length === index + 1;
            const isActive = selectedUser === username;
            const unreadClass = inbox.unreadCount ? 'unread' : '';
            const hasProfileImage = inbox.withUserImg?.indexOf('default_50') === -1;

            // Generate initials - simple and safe
            const getInitials = (name) => {
              const parts = name.split(' ');
              if (parts.length >= 2) {
                return (parts[0][0] + parts[1][0]).toUpperCase();
              }
              return (name[0] + (name[1] || name[0])).toUpperCase();
            };

            const profileName = getInitials(username);

            return (
              <li
                key={inbox.id}
                className={`inbox-message ${isActive ? 'active' : ''} ${unreadClass}`}
                ref={isLastItem ? lastInboxRef : null}
                onClick={() => handleInboxClick(inbox.withUser)}
              >
                {hasProfileImage ? (
                  <img src={inbox.withUserImg} alt={inbox.withUser} />
                ) : (
                  <span className="img-placeholder" style={{ background: '#a7f9e0' }}>
                    {profileName}
                  </span>
                )}
                <div className="about">
                  <div className="title">
                    <span className="date">{renderDate(inbox.lastMessageDate)}</span>
                    <span className="name">{inbox.withUser}</span>
                  </div>
                </div>
                <span className="badge rounded-pill bg-danger unread-count">
                  {inbox.unreadCount || ''}
                </span>
              </li>
            );
          })
        )}
      </ul>
    </div>
  );
};

Inbox.propTypes = {
  isDrawerShown: PropTypes.bool.isRequired,
  setDrawerShown: PropTypes.func.isRequired,
};

export default Inbox;
