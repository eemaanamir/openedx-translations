import { configureStore } from '@reduxjs/toolkit';
import inboxReducer from './slices/inboxSlice';
import messagesReducer from './slices/messagesSlice';
import userReducer from './slices/userSlice';

export const store = configureStore({
  reducer: {
    inbox: inboxReducer,
    messages: messagesReducer,
    user: userReducer,
  },
});

export default store;
