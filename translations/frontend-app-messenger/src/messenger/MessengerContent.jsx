/* eslint-disable jsx-a11y/click-events-have-key-events */
/* eslint-disable jsx-a11y/no-static-element-interactions */
import React, { useState, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { ToastContainer } from 'react-toastify';
import Inbox from './components/Inbox';
import Conversation from './components/Conversation';
import NewMessageModal from './components/newMessageModal';
import { fetchUserProfile } from './store/slices/userSlice';

const MessengerContent = () => {
  const [isDrawerShown, setDrawerShown] = useState(false);
  const dispatch = useDispatch();

  // Fetch current user profile on mount
  useEffect(() => {
    dispatch(fetchUserProfile());
  }, [dispatch]);

  return (
    <div className={isDrawerShown ? 'chat-sidebar-open' : ''}>
      <div className="messenger main-container">
        <Inbox isDrawerShown={isDrawerShown} setDrawerShown={setDrawerShown} />
        <Conversation />
        <div
          className="chat-overlay"
          onClick={() => setDrawerShown(!isDrawerShown)}
        />
      </div>
      <NewMessageModal />
      <ToastContainer />
    </div>
  );
};

export default MessengerContent;
