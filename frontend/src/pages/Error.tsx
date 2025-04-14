import { useRouteError, useNavigate, useLocation } from "react-router";
import { IoMdRefresh } from "react-icons/io";


function ErrorPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const error: any = useRouteError();

  function refreshCurrentPage() {
    navigate(location.pathname);
  }
  
  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 text-center">
        <div className="mb-8">
          <h2 className="mt-6 text-6xl font-extrabold text-gray-900 dark:text-gray-100">{error.statusCode}</h2>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-gray-100">{error.title}</p>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{error.message}</p>
        </div>
        <div className="mt-8">
          <button onClick={refreshCurrentPage}
            className="inline-flex items-center px-4 py-2 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
            <IoMdRefresh size={24}/>
            Refresh
          </button>
        </div>
      </div>
      <div className="mt-16 w-full max-w-2xl">
        <div className="relative">
          <div className="absolute inset-0 flex items-center" aria-hidden="true">
            <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
          </div>
          <div className="relative flex justify-center">
            <span className="px-2 bg-gray-100 dark:bg-gray-800 text-sm text-gray-500 dark:text-gray-400">
              If you think this is a mistake, please contact IT
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ErrorPage;
