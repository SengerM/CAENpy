import setuptools

setuptools.setup(
	name = "CAENpy",
	version = "0.0.0",
	author = "Matias H. Senger",
	author_email = "m.senger@hotmail.com",
	description = "Control CAEN equipment with pure Python",
	url = "https://github.com/SengerM/CAENpy",
	packages = setuptools.find_packages(),
	classifiers = [
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
	],
	install_requires = [
		'pyserial',
		'socket',
		'platform',
	],
)
