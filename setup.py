'''
Install script for PIPyAWC
'''
from setuptools import setup, find_packages

with open('README.md', 'r') as readme_file:
    long_description = readme_file.read()


_DEPENDENCIES_ = [
    'pandas',
    'statsmodels',
    'pyaml',
    'imap-tools',
    'schedule',
    'gpiozero'
    ]

setup(
    name='pipy-awc',
    version='0.5.1',
    description='PiPy Automatic-Water Controller',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Neil Kuehnle',
    author_email='nkuehnle1191@gmail.com',
    license='GPLv2',
    url='https://github.com/nkuehnle/PiPyAWC',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'OSI Approved :: GNU General Public License v2 (GPLv2) ',
        'Natural Language :: English',
        'POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Home Automation',
        'System :: Hardware'
    ],
    keywords=['Raspberry Pi', 'Aquarium', 'Automation', 'AWC', 'RPi'],
    packages=find_packages(),
    install_requires=_DEPENDENCIES_,
    python_requires='~=3.6 ',
    scripts=['bin/PiPy-AWC'],
)
