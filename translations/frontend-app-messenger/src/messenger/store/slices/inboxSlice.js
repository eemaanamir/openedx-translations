import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { toast } from 'react-toastify';
import {
  fetchInboxListService,
  updateUnreadCountService,
  createGroupMessagesService,
} from '../../data/service';

// Async Thunks
export const fetchInboxList = createAsyncThunk(
  'inbox/fetchInboxList',
  async ({ pageNumber, searchQuery }, { rejectWithValue }) => {
    try {
      const data = await fetchInboxListService(pageNumber, searchQuery);
      return { data, pageNumber };
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);

export const updateUnreadCount = createAsyncThunk(
  'inbox/updateUnreadCount',
  async (inboxId, { rejectWithValue }) => {
    try {
      const updatedInbox = await updateUnreadCountService(inboxId);
      return updatedInbox;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);

export const createGroupMessages = createAsyncThunk(
  'inbox/createGroupMessages',
  async ({ receivers, message }, { rejectWithValue }) => {
    try {
      const updatedInbox = await createGroupMessagesService({ receivers, message });
      return updatedInbox;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);

const inboxSlice = createSlice({
  name: 'inbox',
  initialState: {
    list: [],
    selectedUser: '',
    loading: false,
    hasMore: false,
    pageNumber: 1,
    searchQuery: '',
    error: null,
  },
  reducers: {
    setSelectedUser: (state, action) => ({
      ...state,
      selectedUser: action.payload,
    }),
    setSearchQuery: (state, action) => ({
      ...state,
      searchQuery: action.payload,
      pageNumber: 1,
    }),
    incrementPageNumber: (state) => ({
      ...state,
      pageNumber: state.pageNumber + 1,
    }),
    resetPageNumber: (state) => ({
      ...state,
      pageNumber: 1,
    }),
    updateLastMessage: (state, action) => {
      const { username, message } = action.payload;
      const updatedList = state.list.map((item) => {
        if (item.with_user === username || item.withUser === username) {
          return {
            ...item,
            last_message:
              message.length > 30 ? `${message.substring(0, 30)}...` : message,
          };
        }
        return item;
      });

      return {
        ...state,
        list: updatedList,
      };
    },
    updateInboxList: (state, action) => {
      const updatedInbox = action.payload;
      const updatedInboxIds = updatedInbox.map((inbox) => inbox.id);
      const filteredList = state.list.filter((inbox) => !updatedInboxIds.includes(inbox.id));

      return {
        ...state,
        list: [...updatedInbox, ...filteredList],
      };
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Inbox List
      .addCase(fetchInboxList.pending, (state) => ({
        ...state,
        loading: true,
        error: null,
      }))
      .addCase(fetchInboxList.fulfilled, (state, action) => {
        const { data, pageNumber } = action.payload;

        if (pageNumber === 1) {
          return {
            ...state,
            list: data.results,
            selectedUser: data?.results?.length
              ? (data.results[0].withUser || data.results[0].with_user)
              : state.selectedUser,
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
      .addCase(fetchInboxList.rejected, (state, action) => {
        toast.error('Failed to load conversations');
        return {
          ...state,
          loading: false,
          error: action.payload,
        };
      })

      // Update Unread Count
      .addCase(updateUnreadCount.fulfilled, (state, action) => {
        const updatedInbox = action.payload;
        const updatedList = state.list.map((inbox) => (inbox.id === updatedInbox.id ? updatedInbox : inbox));

        return {
          ...state,
          list: updatedList,
        };
      })
      .addCase(updateUnreadCount.rejected, (state) => {
        toast.error('Failed to mark messages as read');
        return state;
      })

      // Create Group Messages
      .addCase(createGroupMessages.fulfilled, (state, action) => {
        const updatedInbox = action.payload;
        const updatedInboxIds = updatedInbox.map((inbox) => inbox.id);
        const filteredList = state.list.filter((inbox) => !updatedInboxIds.includes(inbox.id));

        toast.success('Messages sent successfully');
        return {
          ...state,
          list: [...updatedInbox, ...filteredList],
        };
      })
      .addCase(createGroupMessages.rejected, (state) => {
        toast.error('Failed to send messages');
        return state;
      });
  },
});

export const {
  setSelectedUser,
  setSearchQuery,
  incrementPageNumber,
  resetPageNumber,
  updateLastMessage,
  updateInboxList,
} = inboxSlice.actions;

export default inboxSlice.reducer;
