from setuptools import setup

setup(name='gauthify',
      version='1.01',
      description='API library for GAuthify.com (Google Authenticator, SMS, email multi factor authentication).',
      url='https://www.gauthify.com',
      author='GAuthify',
      author_email='support@gauthify.com',
      license='MIT',
      install_requires=[
          'requests==0.14.1',
      ],
      packages=['gauthify'],
      zip_safe=False)
