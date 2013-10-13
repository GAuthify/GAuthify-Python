import requests
import json
import base64


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

class ConflictError(GAuthifyError):
    """
    Raised when a conflicting result exists (e.g post an existing user)
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
    pass


class GAuthify(object):
    def __init__(self, api_key):
        self.access_points = [
            'https://alpha.gauthify.com/v1/',
            'https://beta.gauthify.com/v1/'
        ]
        self.headers = {
            'Authorization': 'Basic {}'.format(
                base64.b64encode(':{}'.format(api_key))),
            'User-Agent': 'GAuthify-Python/v2.01',
        }

    def request_handler(self, type, url_addon='', params=None, **kwargs):
        """
        Handles API Requests
        """
        json_resp, status_code, req = {}, '', ''
        for base_url in self.access_points:
            try:
                req_url = base_url + url_addon
                req = requests.request(type.lower(), req_url, data=params,
                                       params=params, headers=self.headers,
                                       timeout=5)
                status_code = req.status_code
                json_resp = req.json
                if not isinstance(json_resp, dict) or (status_code > 400 and
                                                               status_code
                                                           not in [
                                                               401, 402, 406,
                                                               404, 409]):
                    raise requests.ConnectionError
                break
            except requests.RequestException, e:
                if base_url == self.access_points[-1]:
                    raise ServerError("Communication error with all access"
                                      "points. Please contact "
                                      "support@gauthify.com for help.",
                                      500, '500', '')
                continue
        if status_code == 401:
            raise ApiKeyError(json_resp['error_message'], status_code,
                              json_resp['error_code'], req.raw)
        if status_code == 402:
            raise RateLimitError(json_resp['error_message'], status_code,
                                 json_resp['error_code'], req.raw)
        elif status_code == 406:
            raise ParameterError(json_resp['error_message'], status_code,
                                 json_resp['error_code'], req.raw)
        elif status_code == 404:
            raise NotFoundError(json_resp['error_message'], status_code,
                                json_resp['error_code'], req.raw)
        elif status_code == 409:
            raise ConflictError(json_resp['error_message'], status_code,
                                json_resp['error_code'], req.raw)
        return json_resp.get('data')


    def create_user(self, unique_id, display_name, email=None,
                    sms_number=None, voice_number=None, meta=None):
        """
        Creates new user
        """
        params = {'unique_id': unique_id, 'display_name': display_name}
        if meta:
            params['meta'] = json.dumps(meta)
        if email:
            params['email'] = email
        if sms_number:
            params['sms_number'] = sms_number
        if voice_number:
            params['voice_number'] = voice_number
        url_addon = "users/"
        return self.request_handler(
            'post', url_addon=url_addon, params=params)


    def update_user(self, unique_id, email=None, sms_number=None,
                    voice_number=None, meta=None, reset_key=False):
        """
        Updates user information
        """
        params = {}
        if email:
            params['email'] = email
        if sms_number:
            params['sms_number'] = sms_number
        if voice_number:
            params['voice_number'] = voice_number
        if meta:
            params['meta'] = json.dumps(meta)
        if reset_key:
            params['reset_key'] = 'true'
        url_addon = "users/{}/".format(unique_id)
        return self.request_handler(
            'put', url_addon=url_addon, params=params)

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

    def get_user(self, unique_id):
        """
        Returns a single user
        """
        url_addon = "users/{}/".format(unique_id)
        return self.request_handler(
            'get', url_addon=url_addon)


    def check_auth(self, unique_id, auth_code, safe_mode=False):
        """
        Checks auth_coded returns True/False depending on correctness.
        """
        try:
            url_addon = 'check/'
            params = {'auth_code': auth_code, 'unique_id': unique_id}
            response = self.request_handler('post', url_addon=url_addon,
                                            params=params)
            return response['authenticated']
        except GAuthifyError, e:
            if safe_mode:
                return True
            else:
                raise e


    def get_user_by_token(self, token):
        """
        Returns a single user by ezGAuth token
        """
        url_addon = "token/"
        params = {'token': token}
        return self.request_handler(
            'post', url_addon=url_addon, params=params)


    def send_sms(self, unique_id, sms_number=None):
        """
        Sends text message to phone number with the one time auth_code
        """

        url_addon = "sms/".format(unique_id)
        params = {'unique_id': unique_id}
        if sms_number:
            params['sms_number'] = sms_number
        return self.request_handler(
            'post', url_addon=url_addon, params=params)


    def send_email(self, unique_id, email=None):
        """
        Sends email with the one time auth_code
        """
        url_addon = "email/".format(unique_id)
        params = {'unique_id': unique_id}
        if email:
            params['email'] = email
        return self.request_handler(
            'post', url_addon=url_addon, params=params)

    def send_voice(self, unique_id, voice_number=None):
        """
        Calls voice_number with the one time auth_code
        """
        url_addon = "voice/".format(unique_id)
        params = {'unique_id': unique_id}
        if voice_number:
            params['voice_number'] = voice_number
        return self.request_handler(
            'post', url_addon=url_addon, params=params)

    def api_errors(self):
        """
        Returns dictionary containing api errors.
        """
        url_addon = "errors/"
        return self.request_handler(
            'get', url_addon=url_addon)

    def quick_test(self, test_email=None, test_sms_number=None,
                   test_voice_number=None):
        """
        Runs initial tests to make sure everything is working fine
        """
        account_name = 'testuser@gauthify.com'
        # Setup
        try:
             self.delete_user(account_name)
        except NotFoundError:
            pass
        def success():
            print("Success \n")

        print("1) Testing Creating a User...")
        result = self.create_user(account_name,
                                  account_name, email='firsttest@gauthify.com',
                                  sms_number='9162627232',
                                  voice_number='9162627234')
        assert result['unique_id'] == account_name
        assert result['display_name'] == account_name
        assert result['email'] == 'firsttest@gauthify.com'
        assert result['sms_number'] == '+19162627232'
        assert result['voice_number'] == '+19162627234'
        print(result)
        success()

        print("2) Retrieving Created User...")
        user = self.get_user(account_name)
        assert isinstance(user, dict)
        print(user)
        success()

        print("3) Retrieving All Users...")
        result = self.get_all_users()
        assert isinstance(result, list)
        print(result)
        success()

        print("4) Bad Auth Code...")
        result = self.check_auth(account_name, '112345')
        assert isinstance(result, bool)
        print(result)
        success()

        print("5) Testing one time pass (OTP)....")
        result = self.check_auth(account_name, user['otp'])
        assert isinstance(result, bool)
        print(result)
        if not result:
            raise ParameterError('Server error. OTP not working. Contact '
                                 'support@gauthify.com for help.', 500, '500',
                                 '')
        success()
        if test_email:
            print("5A) Testing email to {}".format(test_email))
            result = self.send_email(account_name, test_email)
            print(result)
            success()
        if test_sms_number:
            print("5B) Testing SMS to {}".format(test_sms_number))
            self.send_sms(account_name, test_sms_number)
            success()
        if test_voice_number:
            print("5C) Testing Voice to {}".format(test_voice_number))
            self.send_voice(account_name, test_voice_number)
            success()
        print("6) Testing updating email, phone, and meta")
        result = self.update_user(account_name, email='test@gauthify.com',
                                  sms_number='9162627232', meta={'a': 'b'})
        assert result['email'] == 'test@gauthify.com'
        assert result['sms_number'] == '+19162627232'
        assert result['meta']['a'] == 'b'
        current_key = result['key']
        success()

        print("7) Testing key/secret")
        result = self.update_user(account_name, reset_key=True)
        print(current_key, result['key'])
        assert result['key'] != current_key
        success()

        print("8) Deleting Created User...")
        result = self.delete_user(account_name)
        success()

        print("9) Testing backup server...")
        current = self.access_points[0]
        self.access_points[0] = 'https://blah.gauthify.com/v1/'
        result = self.get_all_users()
        self.access_points[0] = current
        print(result)
        success()
