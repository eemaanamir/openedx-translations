import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { toast } from 'react-toastify';
import {
  fetchSelectedInboxMessagesService,
  createMessageService,
} from '../../data/service';

// Async Thunks
export const fetchMessages = createAsyncThunk(
  'messages/fetchMessages',
  async ({ pageNumber, username }, { rejectWithValue }) => {
    try {
      const data = await fetchSelectedInboxMessagesService(pageNumber, username);
      return { data, pageNumber };
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);

export const createMessage = createAsyncThunk(
  'messages/createMessage',
  async ({ receiver, message }, { rejectWithValue }) => {
    try {
      const createdMessage = await createMessageService({ receiver, message });
      return createdMessage;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);

const messagesSlice = createSlice({
  name: 'messages',
  initialState: {
    list: [],
    loading: false,
    hasMore: false,
    pageNumber: 1,
    error: null,
    isReplying: false,
    currentMessage: '',
  },
  reducers: {
    incrementPageNumber: (state) => ({
      ...state,
      pageNumber: state.pageNumber + 1,
    }),
    resetMessages: (state) => ({
      ...state,
      list: [],
      pageNumber: 1,
      hasMore: false,
      isReplying: false,
      currentMessage: '',
    }),
    setIsReplying: (state, action) => ({
      ...state,
      isReplying: action.payload,
    }),
    setCurrentMessage: (state, action) => ({
      ...state,
      currentMessage: action.payload,
    }),
    addMessageToList: (state, action) => ({
      ...state,
      list: [action.payload, ...state.list],
    }),
    clearCurrentMessage: (state) => ({
      ...state,
      currentMessage: '',
      isReplying: false,
    }),
  },
  extraReducers: (builder) => {
    builder
      // Fetch Messages
      .addCase(fetchMessages.pending, (state) => ({
        ...state,
        loading: true,
        error: null,
      }))
      .addCase(fetchMessages.fulfilled, (state, action) => {
        const { data, pageNumber } = action.payload;

        if (pageNumber === 1) {
          return {
            ...state,
            list: data.results,
            hasMore: pageNumber < (data.numPages || data.num_pages),
            loading: false,
          };
        }

        return {
          ...state,
          list: [...state.list, ...data.results],
          hasMore: pageNumber < (data.numPages || data.num_pages),
          loading: false,
        };
      })
      .addCase(fetchMessages.rejected, (state, action) => {
        toast.error('Failed to load conversation');
        return {
          ...state,
          loading: false,
          error: action.payload,
        };
      })

      // Create Message
      .addCase(createMessage.fulfilled, (state, action) => {
        toast.success('Message sent successfully');
        return {
          ...state,
          list: [action.payload, ...state.list],
          currentMessage: '',
          isReplying: false,
        };
      })
      .addCase(createMessage.rejected, (state) => {
        toast.error('Failed to send message');
        return state;
      });
  },
});

export const {
  incrementPageNumber,
  resetMessages,
  setIsReplying,
  setCurrentMessage,
  addMessageToList,
  clearCurrentMessage,
} = messagesSlice.actions;

export default messagesSlice.reducer;
