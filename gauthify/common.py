import requests

class GAuthifyError(Exception):
    """All Errors"""
    def __init__(self, msg, http_status, error_code, response_body):
        super(GAuthifyError, self).__init__(msg)
        self.msg = msg
        self.http_status = http_status
        self.error_code = error_code
        self.response_body = response_body


class ApiKeyError(GAuthifyError):
    """
    Raise when API Key is incorrect
    """
    pass


class ParameterError(GAuthifyError):
    """
    Raised when submitting bad parameters or missing parameters
    """
    pass


class NotFoundError(GAuthifyError):
    """
    Raised when a result isn't found for the parameters provided.
    """
    pass

class ServerError(GAuthifyError):
    """
    Raised for connection issues and any other error that the server can
    give, mainly a 500
    """
    pass


class RateLimitError(GAuthifyError):
    """
    Raised when API limit reached either by lack of payment or membership limit
    """


class GAuthify(object):
    def __init__(self, api_key):
        self.access_points = [
            'https://api.gauthify.com/v1/',
            'https://backup.gauthify.com/v1/'
        ]
        self.headers = {
            'Authorization': api_key,
            'User-Agent': 'GAuthify/v1.00 Python/1.00',
        }

    def request_handler(self, type, url_addon='', params=None, **kwargs):
        """
        Handles API Requests
        """
        for base_url in self.access_points:
            try:
                req_url = base_url + url_addon
                req = requests.request(type.lower(), req_url, data=params,
                               params=params, headers=self.headers, timeout=1.5)
                status_code = req.status_code
                json_resp = req.json
                if not isinstance(json_resp, dict) or (status_code > 400 and
                               status_code not in [401, 402, 406, 404]):
                    raise requests.ConnectionError
                break
            except requests.RequestException, e:
                if base_url == self.access_points[-1]:
                    raise ServerError("Communication error with all access"
                                      "points. Please contact support@gauthify.com for help.", 500, '500', req.raw)
                continue
        if status_code == 401:
            raise ApiKeyError(json_resp['error_message'], status_code, json_resp['error_code'], req.raw)
        if status_code == 402:
            raise RateLimitError(json_resp['error_message'], status_code, json_resp['error_code'], req.raw)
        elif status_code == 406:
            raise ParameterError(json_resp['error_message'], status_code, json_resp['error_code'], req.raw)
        elif status_code == 404:
            raise NotFoundError(json_resp['error_message'], status_code, json_resp['error_code'], req.raw)
        return json_resp.get('data')



    def create_user(self, unique_id, display_name):
        """
        Creates or upserts a new user with a new secret key
        """
        params = {'display_name': display_name}
        url_addon = "users/{}/".format(unique_id)
        return self.request_handler(
            'post', url_addon=url_addon, params=params)

    def delete_user(self, unique_id):
        """
        Deletes user given by unique_id
        """
        url_addon = "users/{}/".format(unique_id)
        return self.request_handler('delete', url_addon=url_addon)

    def get_all_users(self):
        """
        Retrieves a list of all users
        """
        return self.request_handler('get', url_addon='users/')

    def get_user(self, unique_id, auth_code=None):
        """
        Returns a single user, checks the auth_code if provided
        """

        url_addon = "users/{}/".format(unique_id)
        url_addon += 'check/{}/'.format(auth_code) if auth_code else ''
        return self.request_handler(
            'get', url_addon=url_addon)


    def check_auth(self, unique_id, auth_code, safe_mode=False):
        """
        Checks auth_coded returns True/False depending on correctness.
        """
        try:
            response = self.get_user(unique_id, auth_code)
            if not response['provided_auth']:
                raise ParameterError(
                    'auth_code not detected by server. Check if '
                    'params sent via get request.')
            return response['authenticated']
        except GAuthifyError, e:
            if safe_mode:
                return True
            else:
                raise e


    def send_sms(self, unique_id, phone_number):
        """
        Sends text message to phone number with the one time auth_code
        """

        url_addon = "users/{}/".format(unique_id)
        url_addon += 'sms/{}/'.format(phone_number)
        return self.request_handler(
            'get', url_addon=url_addon)


    def send_email(self, unique_id, email):
        """
        Sends email with the one time auth_code
        """

        url_addon = "users/{}/".format(unique_id)
        url_addon += 'email/{}/'.format(email)
        return self.request_handler(
            'get', url_addon=url_addon)


    def quick_test(self, test_email=None, test_number=None):
        """
        Runs initial tests to make sure everything is working fine
        """
        account_name = 'testuser@gauthify.com'

        def success():
            print("Success \n")

        print("1) Testing Creating a User...")
        result = self.create_user(account_name,
                                  account_name)
        print result
        success()

        print("2) Retrieving Created User...")
        user = self.get_user(account_name)
        assert isinstance(user, dict)
        print user
        success()

        print("3) Retrieving All Users...")
        result = self.get_all_users()
        assert isinstance(result, list)
        print result
        success()

        print("4) Bad Auth Code...")
        result = self.check_auth(account_name, '112345')
        assert isinstance(result, bool)
        print result
        success()

        print("5) Testing one time pass (OTP)....")
        result = self.check_auth(account_name, user['otp'])
        assert isinstance(result, bool)
        print result
        if not result:
            raise ParameterError('Server error. OTP not working. Contact '
                                 'support@gauthify.com for help.', 500, '500', '')
        success()
        if test_email:
            print("5A) Testing email to {}".format(test_email))
            result = self.send_email(account_name, test_email)
            print result
            success()
        if test_number:
            print("5B) Testing SMS to {}".format(test_number))
            self.send_sms(account_name, test_number)
            success()
        print("6) Detection of provided auth...")
        result = self.get_user(account_name, 'test12')
        assert result['provided_auth']
        print result
        success()

        print("7) Deleting Created User...")
        result = self.delete_user(account_name)
        assert isinstance(result, bool)
        print result
        success()

        print("8) Testing backup server...")
        self.access_points[0] = 'https://blah.gauthify.com/v1/'
        result = self.get_all_users()
        self.access_points[0] = 'https://api.gauthify.com/v1/'
        print result
        success()


