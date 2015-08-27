#!/bin/bash
#Revision 1
#VTK DEB build script. Call without arguments.
#(c)2013 Uli Koehler. Licensed as CC-By-SA 3.0 DE.
export NAME=libvtk6
export VERSION=6.1.0
export DEBVERSION=${VERSION}-1
#Download and extract the archive
if [ ! -f ${NAME}_${VERSION}.orig.tar.gz ]
then
    wget "http://www.vtk.org/files/release/6.1/VTK-${VERSION}.tar.gz" -O ${NAME}_${VERSION}.orig.tar.gz
fi
rm -rf   VTK-${VERSION}
tar xzvf ${NAME}_${VERSION}.orig.tar.gz
cd VTK-${VERSION}
rm -rf debian
mkdir -p debian
#Use the existing Copyright.txt file
cp Copyright.txt debian/copyright
#Create the changelog (no messages - dummy)
dch --create -v $DEBVERSION --package ${NAME} ""
#Create copyright file
cp Copyright.txt debian/copyright
#Create control file
echo "Source: $NAME" > debian/control
echo "Maintainer: None <none@example.com>" >> debian/control
echo "Section: misc" >> debian/control
echo "Priority: optional" >> debian/control
echo "Standards-Version: 3.9.2" >> debian/control
echo "Build-Depends: debhelper (>= 8), devscripts, build-essential" >> debian/control
#Main library package
echo "" >> debian/control
echo "Package: $NAME" >> debian/control
echo "Architecture: any" >> debian/control
echo "Depends: ${shlibs:Depends}, ${misc:Depends}" >> debian/control
echo "Homepage: https://vtk.org" >> debian/control
echo "Description: VTK - Visualization ToolKit" >> debian/control
#dev package
echo "" >> debian/control
echo "Package: $NAME-dev" >> debian/control
echo "Architecture: all" >> debian/control
echo "Depends: ${shlibs:Depends}, ${misc:Depends}, libvtk6(= $DEBVERSION)" >> debian/control
echo "Homepage: https://vtk.org" >> debian/control
echo "Description: VTK - Visualization ToolKit (development files)" >> debian/control
#Rules files
echo '#!/usr/bin/make -f' > debian/rules
echo '%:' >> debian/rules
echo -e '\tdh $@' >> debian/rules
echo 'override_dh_auto_configure:' >> debian/rules
echo -e "\tcmake -DCMAKE_INSTALL_PREFIX:PATH=`pwd`/debian/${NAME}/usr ." >> debian/rules
echo 'override_dh_auto_build:' >> debian/rules
echo -e '\tmake -j6' >> debian/rules
echo 'override_dh_auto_install:' >> debian/rules
echo -e "\tmkdir -p debian/$NAME/usr debian/$NAME-dev/usr" >> debian/rules
echo -e "\tmake install" >> debian/rules
echo -e "\tmv debian/$NAME/usr/include debian/$NAME-dev/usr" >> debian/rules
#Create some misc files
mkdir -p debian/source
echo "8" > debian/compat
echo "3.0 (quilt)" > debian/source/format
#Build it
debuild -us -uc