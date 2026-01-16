import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { toast } from 'react-toastify';
import { getAuthenticatedUser } from '@edx/frontend-platform/auth';
import { getAccountService, fetchUsersService } from '../../data/service';

// Async Thunks
export const fetchUserProfile = createAsyncThunk(
  'user/fetchUserProfile',
  async (_, { rejectWithValue }) => {
    try {
      const authenticatedUser = getAuthenticatedUser();
      const username = authenticatedUser?.username;
      if (!username) {
        throw new Error('No authenticated user');
      }
      const profileData = await getAccountService(username);
      return { profileData, username };
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);

export const searchUsers = createAsyncThunk(
  'user/searchUsers',
  async (query, { rejectWithValue }) => {
    try {
      const users = await fetchUsersService(query);
      return users;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);

const userSlice = createSlice({
  name: 'user',
  initialState: {
    currentUser: {
      username: '',
      name: '',
      profileName: '',
      hasProfileImage: false,
      profileImage: '',
    },
    searchResults: [],
    loading: false,
    error: null,
  },
  reducers: {
    clearSearchResults: (state) => ({
      ...state,
      searchResults: [],
    }),
  },
  extraReducers: (builder) => {
    builder
      // Fetch User Profile
      .addCase(fetchUserProfile.fulfilled, (state, action) => {
        const { profileData, username } = action.payload;

        return {
          ...state,
          currentUser: {
            username,
            name: username,
            profileName: `${username[0]}${
              username.split(' ')[1] ? username.split(' ')[1][0] : username[1] || ''
            }`,
            hasProfileImage: profileData?.profileImage?.hasImage || false,
            profileImage: profileData?.profileImage?.imageUrlFull || '',
          },
        };
      })
      .addCase(fetchUserProfile.rejected, (state) => {
        // Log error without using console
        toast.error('Failed to fetch profile image');
        return state;
      })

      // Search Users
      .addCase(searchUsers.pending, (state) => ({
        ...state,
        loading: true,
      }))
      .addCase(searchUsers.fulfilled, (state, action) => {
        const mappedResults = action.payload.results.map((user) => ({
          id: user.username,
          username: user.username,
        }));

        return {
          ...state,
          searchResults: mappedResults,
          loading: false,
        };
      })
      .addCase(searchUsers.rejected, (state) => {
        toast.error('Failed to search users');
        return {
          ...state,
          loading: false,
        };
      });
  },
});

export const { clearSearchResults } = userSlice.actions;

export default userSlice.reducer;
