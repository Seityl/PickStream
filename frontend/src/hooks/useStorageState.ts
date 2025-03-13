import { useEffect, useCallback, useReducer } from 'react';

type UseStateHook<T> = [T | null, (value: T | null) => void];

function useAsyncState<T>(initialValue: T | null = null): UseStateHook<T> {
  const [state, setState] = useReducer(
    (_: T | null, action: T | null) => action, initialValue
  );

  return [state, setState];
}

export async function setStorageItemAsync(key: string, value: string | null) {
  try {
    if (value === null) {
      localStorage.removeItem(key);
    } else {
      localStorage.setItem(key, value);
    }
  } catch (e) {
    console.error('Local Storage is unavailable:', e);
  }
}

export function useStorageState(key: string): UseStateHook<string> {
  const storedValue = typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null;
  const [state, setState] = useAsyncState<string>(storedValue);

  useEffect(() => {
    try {
      if (typeof localStorage !== 'undefined') {
        setState(localStorage.getItem(key));
      }
    } catch (e) {
      console.error('Local Storage is unavailable:', e);
    }
  }, [key]);

  const setValue = useCallback(
    (value: string | null) => {
      setState(value);
      setStorageItemAsync(key, value);
    },
    [key]
  );

  return [state, setValue];
}
