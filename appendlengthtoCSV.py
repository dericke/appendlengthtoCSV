# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsDistanceArea,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
    QgsUnitTypes,
)
from qgis import processing

from pathlib import Path
import csv


class ExampleProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    TOTAL_ADDED = "TOTAL_ADDED"
    TOTAL_MODIFIED = "TOTAL_MODIFIED"
    KAART_ADDED = "KAART_ADDED"
    KAART_MODIFIED = "KAART_MODIFIED"
    COUNTRY_NAME = "COUNTRY_NAME"
    OUTPUT = "OUTPUT"

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return ExampleProcessingAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "appendlengthtocsv"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Append length to CSV")

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr("PSQGIS")

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "vectoranalysis"

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr(
            "Calculates the sum of line lengths in each of the input layers and appends to the given CSV"
        )

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TOTAL_ADDED, self.tr("Total added"), [QgsProcessing.TypeVectorLine]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TOTAL_MODIFIED,
                self.tr("Total modified"),
                [QgsProcessing.TypeVectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.KAART_ADDED, self.tr("Kaart added"), [QgsProcessing.TypeVectorLine]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.KAART_MODIFIED,
                self.tr("Kaart modified"),
                [QgsProcessing.TypeVectorLine],
            )
        )

        self.addParameter(
            QgsProcessingParameterString(self.COUNTRY_NAME, self.tr("Country name"))
        )

        fileDest = QgsProcessingParameterFileDestination(
            self.OUTPUT, self.tr("Output csv"), "CSV Files (*.csv)", None, False, False
        )

        fileDest.setMetadata({"widget_wrapper": {"dontconfirmoverwrite": True}})

        self.addParameter(fileDest)

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        distance_measure = QgsDistanceArea()
        distance_measure.setEllipsoid("GRS80")

        unittype = QgsUnitTypes.toString(distance_measure.lengthUnits())

        feedback.pushInfo(f"Length units are {unittype}")

        sources = {
            "total_added": self.parameterAsSource(
                parameters, self.TOTAL_ADDED, context
            ),
            "total_modified": self.parameterAsSource(
                parameters, self.TOTAL_MODIFIED, context
            ),
            "kaart_added": self.parameterAsSource(
                parameters, self.KAART_ADDED, context
            ),
            "kaart_modified": self.parameterAsSource(
                parameters, self.KAART_MODIFIED, context
            ),
        }

        country_name = self.parameterAsString(parameters, self.COUNTRY_NAME, context)

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        for v in sources.values():
            if v is None:
                raise QgsProcessingException(
                    self.invalidSourceError(parameters, self.INPUT)
                )

        dest_path = Path(self.parameterAsFileOutput(parameters, self.OUTPUT, context))

        distances = {}
        for name, layer in sources.items():
            sumlength = sum(
                distance_measure.measureLength(feature.geometry())
                for feature in layer.getFeatures()
            )
            feedback.pushInfo(f"{name} is {sumlength} kilometers.")
            distances[name] = round(
                distance_measure.convertLengthMeasurement(
                    sumlength, QgsUnitTypes.DistanceKilometers
                )
            )

        with dest_path.open("a") as f:
            rows_to_write = (
                [] if f.tell() else [("Country", "Data Change", "Kaart", "Total")]
            )
            rows_to_write += [
                (
                    country_name,
                    "Km of road added",
                    distances["kaart_added"],
                    distances["total_added"],
                ),
                (
                    country_name,
                    "Km of road edited or modified",
                    distances["kaart_modified"],
                    distances["total_modified"],
                ),
            ]
            thewriter = csv.writer(f, delimiter=",")
            thewriter.writerows(rows_to_write)

        return {self.OUTPUT: str(dest_path)}
