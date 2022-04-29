import pathlib
import os
from subprocess import check_call
from setuptools.command.develop import develop
from setuptools import find_packages, setup


def generate_proto_code():
    proto_interface_dir = "./proto"
    generated_src_dir = "./aiobafi6/generated/"
    out_folder = "aiobafi6"
    if not os.path.exists(generated_src_dir):
        os.mkdir(generated_src_dir)
    proto_it = pathlib.Path().glob(proto_interface_dir + "/**/*")
    proto_path = "generated=" + proto_interface_dir
    protos = [str(proto) for proto in proto_it if proto.is_file()]
    check_call(
        ["protoc"] + protos + ["--python_out", out_folder, "--proto_path", proto_path]
    )


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
    description="Big Ass Fans i6 protocol asynchronous Python library",
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
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Framework :: AsyncIO",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Home Automation",
    ],
    keywords="BigAssFans i6 Haiku HaikuHome SenseME fan home automation assistant",
    python_requires=">=3.9",
)
