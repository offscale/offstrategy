#!/usr/bin/env python

from __future__ import print_function
from sys import version

if version[0] == "2":
    from urllib import urlopen
else:
    from urllib.request import urlopen


def get_ubuntu_ami(
    region="ap-southeast-2",
    arch="64-bit",
    root_store="ebs",
    codename="trusty",
    version="current",
):
    s = (
        urlopen(
            "http://cloud-images.ubuntu.com/{codename}/{version}/".format(
                codename=codename, version=version
            )
        )
        .read()
        .replace(" ", "")
    )
    print(
        "http://cloud-images.ubuntu.com/{codename}/{version}/".format(
            codename=codename, version=version
        )
    )
    find = """<tr>
<td><p>{region}</p></td>
<td><p>{arch}</p></td>
<td><p>{root_store}</p></td>
<td><p><buttontype="button"onClick="parent.location='https://console.aws.amazon.com/ec2/home?region={region}#launchAmi=
    """.format(
        region=region, arch=arch, root_store=root_store
    ).rstrip()
    return (lambda first: s[first + len(find) : s.find("'", first + len(find))])(
        s.find(find)
    )


if __name__ == "__main__":
    print(get_ubuntu_ami())
