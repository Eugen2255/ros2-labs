from setuptools import find_packages, setup

package_name = 'patrol'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    package_data={'': ['py.typed']},
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Eugen',
    maintainer_email='kirillov2255@yandex.ru',
    description='First node: follows turtlesim pose and publishes Twist commands',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'patrol = patrol.patrol:main',
            'pose_relay = patrol.pose_relay:main',
            'pose_listener = patrol.pose_listener:main',
        ],
    },
)
