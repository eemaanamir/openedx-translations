/* eslint-disable import/no-extraneous-dependencies */
import 'core-js/stable';
import 'regenerator-runtime/runtime';

import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min';

import $ from 'jquery';

import 'react-toastify/dist/ReactToastify.css';

import {
  APP_INIT_ERROR, APP_READY, subscribe, initialize,
} from '@edx/frontend-platform';
import { AppProvider, ErrorPage } from '@edx/frontend-platform/react';
import { createRoot } from 'react-dom/client';

import Header from '@edx/frontend-component-header';
import { FooterSlot } from '@edx/frontend-component-footer';
import messages from './i18n';

import { store } from './messenger/store';
import MessengerContent from './messenger/MessengerContent';

import './index.scss';

window.jQuery = $;
window.$ = $;

const rootNode = createRoot(document.getElementById('root'));
subscribe(APP_READY, () => {
  rootNode.render(
    <AppProvider store={store}>
      <Header />
      <MessengerContent />
      <FooterSlot />
    </AppProvider>,
  );
});

subscribe(APP_INIT_ERROR, (error) => {
  rootNode.render(<ErrorPage message={error.message} />);
});

initialize({
  messages,
});
