import arcpy, numpy
#constants
FEATURE_CLASS_LAYER = "fc_layer"
FEATURE_GROUPS_FREQUENCY = "feature_groups_frequency"
SPACER = "    "
groupIDs = [0]

def addNewGroupID():
    newgroupid = len(groupIDs)
    groupIDs.append(newgroupid)
    return newgroupid
        
def getGroupID(groups_for_overlapping_features):
    if len(set(groupIDs) - set(groups_for_overlapping_features)) == 0:
        return addNewGroupID()
    else:
        valid_group_ids = list((set(groupIDs) - set(groups_for_overlapping_features)))
        group_id = valid_group_ids[len(valid_group_ids) - 1] 
        if group_id == 0:
            group_id = addNewGroupID()
        return group_id

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "JRC Tools"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [TabulateAreaForFeatureDataset, ExplodeOverlappingPolygons]


class TabulateAreaForFeatureDataset(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "TabulateArea for FeatureDataset"
        self.description = "Iterates through all feature classes in a feature dataset and computes the zonal statistics for each feature class and appends the results into a single output table"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = None
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return

class ExplodeOverlappingPolygons(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Explode overlapping polygons"
        self.description = "Creates a new set of feature classes from a feature class that remove all overlapping polygons."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Input feature class",
            name="fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")
        return [param0]

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        fc = parameters[0].valueAsText
        desc = arcpy.Describe(fc)
        arcpy.env.overwriteOutput = True
        # get the overlaps from the topology
        arcpy.env.workspace = r"E:\cottaan\My Documents\ArcGIS\PA GLC2000 Analysis\default.gdb"
        arcpy.AddMessage("STEP 1: Getting overlapping features")
        arcpy.AddMessage(SPACER + "Creating topology")
        arcpy.CreateTopology_management('featuredataset', "topo1")
        arcpy.AddMessage(SPACER + "Adding feature class to topology")
        arcpy.AddFeatureClassToTopology_management("featuredataset/topo1", fc, "1", "1")
        arcpy.AddMessage(SPACER + "Adding topology rule")
        arcpy.AddRuleToTopology_management("featuredataset/topo1", "Must Not Overlap (Area)", fc, "#", "#", "#")
        arcpy.AddMessage(SPACER + "Validating topology")
        arcpy.ValidateTopology_management('featuredataset/topo1')
        arcpy.AddMessage(SPACER + "Exporting topology errors")
        arcpy.ExportTopologyErrors_management("featuredataset/topo1", "featuredataset", "topoerrors")  # errors will be in topoerrors_poly
        arcpy.AddMessage(SPACER + "Getting unique overlapping polygons")
        arcpy.Frequency_analysis("featuredataset/topoerrors_poly", "topoerrors_poly_Frequency", "OriginObjectID;DestinationObjectID", "#")  # get the unique overlapping features
        arcpy.CopyRows_management("topoerrors_poly_Frequency", "topoerrors_poly_Frequency2", "#")  # copy the table so we can append the inverse overlapping features
        arcpy.Append_management("topoerrors_poly_Frequency2", "topoerrors_poly_Frequency", "NO_TEST", """FREQUENCY "FREQUENCY" true true false 4 Long 0 0 ,First,#,topoerrors_poly_Frequency2,FREQUENCY,-1,-1;OriginObjectID "Feature 1" true true false 4 Long 0 0 ,First,#,topoerrors_poly_Frequency2,DestinationObjectID,-1,-1;DestinationObjectID "Feature 2" true true false 4 Long 0 0 ,First,#,topoerrors_poly_Frequency2,OriginObjectID,-1,-1""", "#")  # append the inverse overlapping features
        arcpy.Delete_management(r'topoerrors_poly_Frequency2')  # delete the temporary table
        arcpy.AddMessage(SPACER + "Getting the count of overlapping polygons")
        arcpy.Frequency_analysis("topoerrors_poly_Frequency", "unique_overlaps", "OriginObjectID", "#")  # create the unique overlaps table which will have the FREQUENCY, feature1 OBJECTID
        arcpy.Sort_management("unique_overlaps", "unique_OriginObjectIDs", "FREQUENCY DESCENDING", "UR")
        arcpy.AddMessage(SPACER + "Adding an overlap count field to the unique overlaps")
        arcpy.AddField_management("topoerrors_poly_Frequency", "overlap_count", "SHORT", "#", "#", "255", "#", "NULLABLE", "NON_REQUIRED", "#")
        arcpy.AddMessage(SPACER + "Adding a group field to compute the disjoint collection of features")
        arcpy.AddField_management("topoerrors_poly_Frequency", "grp", "LONG", "#", "#", "255", "#", "NULLABLE", "NON_REQUIRED", "#")
        arcpy.AddMessage(SPACER + "Adding indexes to speed up the joins")
        arcpy.AddIndex_management("topoerrors_poly_Frequency", "OriginObjectID;DestinationObjectID", "index1", "NON_UNIQUE", "NON_ASCENDING")
        arcpy.AddMessage(SPACER + "Joining unique overlapping polygon table to frequency table")
        arcpy.MakeTableView_management(r'topoerrors_poly_Frequency', "topoerrors_poly_Frequency_tv")  # make a table view of the table
        arcpy.MakeTableView_management(r'unique_overlaps', "unique_overlaps_tv")  # make a table view of the table
        arcpy.AddJoin_management("topoerrors_poly_Frequency_tv", "OriginObjectID", "unique_overlaps_tv", "OriginObjectID", "KEEP_ALL")
        arcpy.AddMessage(SPACER + "Populating the overlap count field")
        arcpy.CalculateField_management("topoerrors_poly_Frequency_tv", "overlap_count", "[unique_overlaps.FREQUENCY]", "VB", "#")
        arcpy.AddMessage(SPACER + "Removing join")
        arcpy.RemoveJoin_management("topoerrors_poly_Frequency_tv", "unique_overlaps")
        arcpy.AddMessage(SPACER + "Sorting data to compute groups")
        arcpy.Delete_management("topoerrors_poly_Frequency_tv")
        arcpy.Delete_management("unique_overlaps_tv")
        arcpy.Sort_management("topoerrors_poly_Frequency", "unique_overlaps_sorted", "overlap_count DESCENDING", "UR")
        arcpy.AddMessage(SPACER + "Deleting the temporary tables")
        arcpy.Delete_management(r'unique_overlaps')  # delete the temporary table
        arcpy.Delete_management(r'topoerrors_poly_Frequency')  # delete the temporary table
        arcpy.AddMessage(SPACER + "Deleting the topologies")
        arcpy.Delete_management(r'featuredataset\topo1')  # delete the topology
        arcpy.Delete_management(r'featuredataset\topoerrors_line')  # delete the line topo errors
        arcpy.Delete_management(r'featuredataset\topoerrors_point')  # delete the point topo errors
        arcpy.Delete_management(r'featuredataset\topoerrors_poly')  # delete the poly topo errors
        # create the non-overlapping feature groups
        arcpy.AddMessage("STEP 2: Creating the groups of non-overlapping features")
        arcpy.AddMessage(SPACER + "Iterating through the features to created the groups")
        unique_origin_ids = [int(t[0]) for t in arcpy.da.TableToNumPyArray("unique_OriginObjectIDs", "OriginObjectID").tolist()]
        feature_groups = arcpy.da.TableToNumPyArray("unique_overlaps_sorted", ["OriginObjectID", "DestinationObjectID", "overlap_count", "grp"], null_value=0)
        for unique_origin_id in unique_origin_ids:
        #     arcpy.AddMessage(SPACER + SPACER + "Feature: " + str(unique_origin_id))
            overlapping_feature_ids = feature_groups[numpy.where(feature_groups['OriginObjectID'] == unique_origin_id)]['DestinationObjectID']
        #     arcpy.AddMessage(SPACER + SPACER + "Overlapping features: " + ",".join([str(id) for id in overlapping_feature_ids]))
            groups_for_overlapping_features = list(set(feature_groups[numpy.in1d(feature_groups['OriginObjectID'], overlapping_feature_ids)]['grp']))
        #     arcpy.AddMessage(SPACER + SPACER + "Overlapping feature groups: " + ",".join([str(id) for id in groups_for_overlapping_features]))
            groupID = getGroupID(groups_for_overlapping_features)
        #     arcpy.AddMessage(SPACER + SPACER + "Assigning group " + str(groupID) + " to feature " + str(unique_origin_id))
            for i in numpy.where(feature_groups['OriginObjectID'] == unique_origin_id)[0]:
                feature_groups[i]['grp'] = groupID
        arcpy.AddMessage(SPACER + "Deleting the temporary tables")
        arcpy.Delete_management('unique_OriginObjectIDs')  # delete the unique_OriginObjectIDs table
        arcpy.Delete_management('unique_overlaps_sorted')  # delete the unique_overlaps_sorted table
        arcpy.AddMessage(SPACER + "Creating final output table of non-overlapping feature groups")        
        table_name = arcpy.env.workspace + "/feature_groups"
        arcpy.da.NumPyArrayToTable(feature_groups, table_name)
        arcpy.AddMessage(SPACER + "Getting the unique feature groups")
        arcpy.Frequency_analysis("feature_groups", "feature_groups_Frequency1", "OriginObjectID;grp", "#")
        arcpy.Delete_management("feature_groups")
        arcpy.AddMessage(SPACER + "Adding the grp field to the feature class")
        arcpy.JoinField_management(fc, "OBJECTID", "feature_groups_Frequency1", "OriginObjectID", "grp")
        arcpy.Delete_management("feature_groups_Frequency1")
        arcpy.AddMessage(SPACER + "Creating group 0 for non-overlapping features")
        arcpy.MakeFeatureLayer_management(fc, FEATURE_CLASS_LAYER)
        arcpy.SelectLayerByAttribute_management(FEATURE_CLASS_LAYER, "NEW_SELECTION", "grp IS Null")
        count = arcpy.GetCount_management(FEATURE_CLASS_LAYER)
        arcpy.AddMessage(SPACER + str(count) + " records selected")
        arcpy.CalculateField_management(FEATURE_CLASS_LAYER, "grp", "0", "VB", "#")
        arcpy.SelectLayerByAttribute_management(FEATURE_CLASS_LAYER, "CLEAR_SELECTION")
        arcpy.AddMessage(SPACER + "Getting the unique non-overlapping feature groups to export")
        arcpy.Frequency_analysis(FEATURE_CLASS_LAYER, FEATURE_GROUPS_FREQUENCY, "grp", "#")
        unique_non_overlapping_groups = arcpy.da.TableToNumPyArray(FEATURE_GROUPS_FREQUENCY, "grp").tolist()
        arcpy.Delete_management(FEATURE_GROUPS_FREQUENCY)
        # Exporting the groups of non-overlapping features
        arcpy.AddMessage("STEP 3: Exporting the groups of non-overlapping features")
        arcpy.AddMessage(SPACER + "Creating the feature dataset")
        arcpy.CreateFeatureDataset_management(arcpy.env.workspace, "feature_groups", "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 10000;8.98315284119522E-09;0.001;0.001;IsHighPrecision")
        for unique_non_overlapping_group in unique_non_overlapping_groups:
            group_id = str(unique_non_overlapping_group[0])
            arcpy.AddMessage(SPACER + SPACER + "Exporting group " + group_id)
            expression = "grp = " + group_id
            arcpy.SelectLayerByAttribute_management(FEATURE_CLASS_LAYER, "NEW_SELECTION", expression)
            arcpy.FeatureClassToFeatureClass_conversion(FEATURE_CLASS_LAYER, "feature_groups", desc.name + "_" + str(group_id).zfill(3))
        arcpy.AddMessage(SPACER + "Deleting the temporary tables and the grp field from the feature class")
        arcpy.Delete_management(FEATURE_CLASS_LAYER)
        arcpy.DeleteField_management(fc, "grp")
        return