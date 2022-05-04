import pathlib
from subprocess import check_call

from setuptools import find_packages, setup
from setuptools.command.develop import develop


def generate_proto_code():
    proto_it = pathlib.Path().glob("./proto/**/*")
    protos = [str(proto) for proto in proto_it if proto.is_file()]
    check_call(["protoc", "--python_out=aiobafi6", "--pyi_out=aiobafi6"] + protos)


class CustomDevelopCommand(develop):
    """Wrapper for custom commands to run before package installation."""

    uninstall = False

    def run(self):
        develop.run(self)

    def install_for_development(self):
        develop.install_for_development(self)
        generate_proto_code()


setup(
    name="aiobafi6",
    version="0.1.0",
    description="Big Ass Fans i6/Haiku protocol asynchronous Python library",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="jfroy",
    author_email="jf@devklog.net",
    url="https://github.com/jfroy/aiobafi6",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["protobuf~=3.20", "zeroconf~=0.38"],
    license="Apache 2.0",
    cmdclass={
        "develop": CustomDevelopCommand,
    },
    entry_points={
        "console_scripts": ["aiobafi6 = aiobafi6.cmd.main:main"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Framework :: AsyncIO",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Home Automation",
    ],
    keywords="BigAssFans i6 Haiku HaikuHome SenseME fan home automation assistant",
    python_requires=">=3.8",
)
