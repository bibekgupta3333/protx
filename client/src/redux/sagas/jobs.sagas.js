import { put, takeLatest, takeLeading, call } from 'redux-saga/effects';
import 'cross-fetch';
import Cookies from 'js-cookie';
import { fetchUtil } from 'utils/fetchUtil';

export function* getJobs(action) {
  yield put({ type: 'SHOW_SPINNER' });
  const url = new URL('/api/workspace/jobs', window.location.origin);
  Object.keys(action.params).forEach(key =>
    url.searchParams.append(key, action.params[key])
  );
  try {
    const res = yield call(fetch, url, {
      credentials: 'same-origin',
      ...action.options
    });
    const json = yield res.json();
    yield put({ type: 'JOBS_LIST', payload: json.response });
    yield put({ type: 'HIDE_SPINNER' });
  } catch {
    yield put({ type: 'JOBS_LIST', payload: [{ error: 'err!' }] });
    yield put({ type: 'HIDE_SPINNER' });
  }
}

function* submitJob(action) {
  yield put({ type: 'FLUSH_SUBMIT' });
  yield put({ type: 'TOGGLE_SUBMITTING' });
  try {
    const res = yield call(fetchUtil, {
      url: '/api/workspace/jobs',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': Cookies.get('csrftoken')
      },
      body: JSON.stringify(action.payload)
    });
    if (res.response.execSys) {
      yield put({
        type: 'SYSTEMS_TOGGLE_MODAL',
        payload: {
          operation: 'pushKeys',
          props: {
            onSuccess: { type: 'SUBMIT_JOB', payload: action.payload },
            system: res.response.execSys
          }
        }
      });
      yield put({ type: 'TOGGLE_SUBMITTING' });
    } else {
      yield put({
        type: 'SUBMIT_JOB_SUCCESS',
        payload: res.response
      });
    }
  } catch (error) {
    yield put({
      type: 'SUBMIT_JOB_ERROR',
      payload: error
    });
  }
}

export function* watchJobs() {
  yield takeLatest('GET_JOBS', getJobs);
  yield takeLeading('SUBMIT_JOB', submitJob);
}