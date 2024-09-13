# from lxml import etree as ET
import xml.etree.ElementTree as ET #TODO deprecated, use lxml instead!
import re
import time
import os
import sys
import uuid
from copy import deepcopy
from pprint import pp
from files_data2 import Master, Playlist, Resolution

#PT0H1M59.89S
def seconds(time):
    s=0
    m=re.search("([0-9.]+)H",time)
    if m: s=s+float(m.group(1))*3600
    m=re.search("([0-9.]+)M",time)
    if m: s=s+float(m.group(1))*60
    m=re.search("([0-9.]+)S",time)
    if m: s=s+float(m.group(1))
    return s

#119.89
def iso8601(s):
    h=int(s/3600)
    s=s-h*3600
    m=int(s/60)
    s=s-m*60
    return 'PT{0:1g}H{1:1g}M{2:1g}S'.format(h,m,s)

def ns(tag):
    return "{urn:mpeg:dash:schema:mpd:2011}"+tag


def get_format(AdaptationSet, Representation):
    if((Representation.get('mimeType') == 'video/mp4') or (AdaptationSet.get('mimeType') == 'video/mp4') or (AdaptationSet.get('contentType') == 'video')): return 'video'
    if((Representation.get('mimeType') == 'audio/mp4') or (AdaptationSet.get('mimeType') == 'audio/mp4') or (AdaptationSet.get('contentType') == 'audio')): return 'audio'

ET.register_namespace('','urn:mpeg:dash:schema:mpd:2011')

ad_tpl=ET.fromstring("""<?xml version="1.0" encoding="utf-8"?>
<MPD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns="urn:mpeg:dash:schema:mpd:2011"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        xsi:schemaLocation="urn:mpeg:DASH:schema:MPD:2011 http://standards.iso.org/ittf/PubliclyAvailableStandards/MPEG-DASH_schema_files/DASH-MPD.xsd"
        profiles="urn:mpeg:dash:profile:isoff-live:2011"
        type="static"
        mediaPresentationDuration="PT0.00S"
        minBufferTime="PT16.6S">
        <ProgramInformation>
        </ProgramInformation>
        <Period id="0" start="PT0.0S">
                <AdaptationSet id="0" contentType="video" segmentAlignment="true" bitstreamSwitching="true" lang="und">
                        <Representation id="0" mimeType="video/mp4" codecs="avc1.640028" bandwidth="10000" width="1920" height="1080" frameRate="30000/1001">
                                <SegmentTemplate timescale="2000" initialization="init-stream0.m4s" media="chunk-stream0-$Number%05d$.m4s" startNumber="1">
                                </SegmentTemplate>
                        </Representation>
                </AdaptationSet>
                <AdaptationSet id="1" contentType="audio" segmentAlignment="true" bitstreamSwitching="true" lang="und">
                        <Representation id="1" mimeType="audio/mp4" codecs="mp4a.40.2" bandwidth="128000" audioSamplingRate="48000">
                                <AudioChannelConfiguration schemeIdUri="urn:mpeg:dash:23003:3:audio_channel_configuration:2011" value="2" />
                                <SegmentTemplate timescale="3000" initialization="init-stream1.m4s" media="chunk-stream1-$Number%05d$.m4s" startNumber="1">
                                </SegmentTemplate>
                        </Representation>
                </AdaptationSet>
        </Period>
</MPD>""")

class DashMasterPlaylistReader(object):
    def __init__(self, filepath):
        # We assume, we read a mpd file

        if not os.path.exists(filepath) or not filepath.endswith(".mpd"):
            raise ValueError("not a directory and does not point to a .mpd file")
        self.origin_file = filepath
        self.directory = os.path.dirname(filepath)

    #determine each stream from the manifest as object
    def process_stream(self):
        streams = []

        with open(self.origin_file, "r") as input_file:

            root=ET.fromstring(input_file.read())
            mediaPresentationDuration = 0
            if 'mediaPresentationDuration' in root.attrib:
                mediaPresentationDuration=seconds(root.attrib["mediaPresentationDuration"])

            Periods=root.findall(ns("Period"))
            for Period in Periods:
                period_id = str(Period.get('id'))
                period_grp_id = uuid.uuid4()
                period_start = Period.get('start')

                #check & init variant if not exist
                for AdaptationSet in Period.findall(ns("AdaptationSet")):
                    for Representation in AdaptationSet.findall(ns("Representation")):
                        representation_id = Representation.get('id')
                        stream = {} #playlist variant (= 1 Representation)
                        stream["playlist"] = self.origin_file #TODO ??
                        stream["dirname"] = self.directory
                        stream['contentType'] = get_format(AdaptationSet, Representation)
                        stream['BANDWIDTH'] = Representation.get('bandwidth')
                        stream['RESOLUTION'] = Resolution(Representation.get('width'), Representation.get('height'))
                        stream['representation_id'] = representation_id
                        stream['segments'] = []

                        #avoid duplicates streams per period
                        pid_stream_is_exist:bool = False
                        for idx in range(len(streams)):
                            for seg in streams[idx]['segments']:
                                if(((stream['contentType'] == 'audio') and ((streams[idx]['BANDWIDTH']==stream['BANDWIDTH']))) and (seg['period_id'] == period_id)):
                                    pid_stream_is_exist = True
                                    continue

                        if(not pid_stream_is_exist):
                            #get segments for current period
                            for SegmentTemplate in Representation.findall(ns("SegmentTemplate")):
                                timescale = int(SegmentTemplate.get('timescale'))
                                initialization = str(SegmentTemplate.get('initialization'))
                                media = str(SegmentTemplate.get('media'))
                                for S in SegmentTemplate.findall(ns("SegmentTimeline")+"/"+ns("S")):
                                    if "t" in S.attrib: t=int(S.attrib["t"]) #segment offset in timescale unit
                                    d=int(S.attrib["d"]) #segment duration in timescale unit
                                    r=int(S.attrib["r"]) if "r" in S.attrib else 0 #nb of similar consecutive segments
                                    seg_tl_duration = (d*(r+1))/timescale
                                    seg_tl = dict(
                                        period_grp_id=period_grp_id,
                                        period_id=str(period_id),
                                        period_start=seconds(period_start),
                                        representation_id=representation_id,
                                        initialization=initialization,
                                        media=media,
                                        timescale=timescale,
                                        timeline=(t,d,r),
                                        duration=seg_tl_duration,
                                    )
                                    stream['segments'].append(seg_tl) #TODO segments or segmentsTLs ?? => (seg, seg_tl)

                            #update existing stream with segments or insert complete new stream (video or audio)
                            if len(streams) > 0 :
                                count_update = 0
                                for idx in range(len(streams)):
                                    s = streams[idx]

                                    if(
                                        ((stream['contentType'] == 'video') and ((s['BANDWIDTH']==stream['BANDWIDTH']) and (s['RESOLUTION'].get_resolution()==stream['RESOLUTION'].get_resolution())))
                                        or
                                        ((stream['contentType'] == 'audio') and ((s['BANDWIDTH']==stream['BANDWIDTH'])))
                                    ):
                                        streams[idx]['segments'] = streams[idx]['segments'] + stream['segments'] #add segments over periods into existing stream 
                                        count_update+=1
                                    
                                #insert new stream if not exist
                                if count_update==0:
                                    streams.append(stream)
                            else:
                                streams.append(stream) #init streams with new stream

            # pp("DashMasterPlaylistReader#process_stream#streams : ")
            # pp(streams)
            
            return Master(
                filepath=self.origin_file,
                directory=os.path.dirname(self.origin_file),
                playlists=[Playlist(playlist_infos=stream) for stream in streams],
                headers={
                    'mediaPresentationDuration': mediaPresentationDuration
                },
            )

class DashMerger():
    def __init__(self, input, ads_and_timestamps):
        self.input = input
        self.ads = ads_and_timestamps
        self.output_streams = dict(
            video=[],
            audio=[]
        )

    #FOR NOW WE GO WITH SEG TIMELINE APPROACH, THE IDEA IS TO INSERT AD STREAM SEGS BASED ON PERIOD POSITION ONLY
    #TODO MAYBE NEXT, WITH SEG PLAYLIST, be able to insert ads based on segments position also ??
    def process_streams(self):
        sorted_ads = sorted(self.ads, key=lambda x: x["timestamp"])

        for main_stream in self.input.playlists:
            content_type = main_stream.headers.get('contentType')
            period_grp_id = None
            seq:int = 0
            period_start: float = 0.0
            total_content_duration: float = 0.0 #result main video segments duration
            total_duration: float = 0.0 #result main video & ad segments duration
            final_segments = []
    
            for main_seg in main_stream.segments:      
                #detect period changes in main_video
                if(period_grp_id != main_seg['period_grp_id']):
                    period_grp_id = main_seg['period_grp_id']
                    period_start = total_duration

                for ad in sorted_ads:
                    #check if we are at ad insertion position
                    if (
                        total_content_duration
                        <= ad["timestamp"]
                        <= total_content_duration + main_seg['duration']
                    ):
                        for ad_stream in ad['master'].playlists:
                            #take only ad_stream which match with main_stream formats (contentType, BW, resolution)
                            if(
                                ((ad_stream.headers.get('contentType') == 'video') and (main_stream.headers.get('contentType') == 'video') and ((main_stream.headers.get('bandwidth')==ad_stream.headers.get('bandwidth') and (main_stream.resolution.get_resolution()==ad_stream.resolution.get_resolution()))))
                                or
                                ((ad_stream.headers.get('contentType') == 'audio') and ((main_stream.headers.get('bandwidth')==ad_stream.headers.get('bandwidth'))))
                            ):
                                #Insert AD Period
                                for ad_seg in ad_stream.segments:
                                    ad_seg['period_start'] = period_start
                                    ad_seg['seg_type'] = 'ad'
                                    final_segments.append(ad_seg)
                                    total_duration += ad_seg['duration'] #total duration augmented with ad seg duration

                                period_start = total_duration

                main_seg['period_start'] = period_start
                main_seg['seg_type'] = 'main'

                #Insert Main seg
                final_segments.append(main_seg)

                total_content_duration += main_seg['duration']
                total_duration += main_seg['duration']

            #update each seg period_id sequence order
            prev_seg = final_segments[0]
            for i in range(len(final_segments)):
                if(final_segments[i]['period_grp_id'] != prev_seg['period_grp_id']):
                    seq+=1
                final_segments[i]['old_period_id'] = final_segments[i]['period_id'] #keep track of initial period id
                final_segments[i]['period_id'] = seq #new period id
                prev_seg = final_segments[i]

            output = dict(
                content_type=content_type,
                resolution=main_stream.resolution,#.get_resolution(),
                bandwidth=main_stream.headers['bandwidth'],
                total_content_duration=total_content_duration,
                total_duration=total_duration,
                segments=final_segments
            )

            self.output_streams[content_type].append(output)
        
        print('output_streams: ')
        pp(self.output_streams)
    
    def find_streams(self):
        return

#update dash manifest based on merged object streams (include main, ad streams)
class DashMainManifestEditor():
    def __init__(self, main_mpd,merged_streams,ad_tpl):

        with open(main_mpd, "r") as input_file:
            self.root=ET.fromstring(input_file.read())
            self.final_manifest = None
            self.manifest = ET.Element(self.root.tag, self.root.attrib)
            self.merged_streams = merged_streams
            self.ad_tpl = ad_tpl

    def set_media_presentation_duration(self,duration):
        self.manifest.set('mediaPresentationDuration', iso8601(duration))

    #build as mpd
    def to_mpd(self):
        #set mediaPresentationDuration
        total_duration = self.merged_streams['video'][1]['total_duration'] #get total duration by using one stream example
        self.set_media_presentation_duration(total_duration)

        origin_periods=self.root.findall(ns("Period")) #from origin manifest
        period_grp_id = None
        ar_count=0 #stream adaptation/representation count id

        for merged_seg in self.merged_streams['video'][1]['segments']: #TODO dynamically select one stream with AD
            #detect merged_streams period changes
            if(period_grp_id != merged_seg['period_grp_id']):
                period_grp_id = merged_seg['period_grp_id']
                
                #We need to insert a new AD Period
                if merged_seg['seg_type'] == 'ad':

                    AdPeriod = ET.SubElement(
                        self.manifest,
                        ns("Period"),
                        {
                            "id":str(merged_seg['period_id']),
                            "start":str(iso8601(merged_seg['period_start'])) #TODO duration or start?
                        }
                    )
                    
                    #Enrich created AD Period all streams sub-elements
                    #We need to update with same period, all sub-elements for each streams
                    #So we based on the merged streams
                    for merged_stream in self.merged_streams['video']:
                        for seg in merged_stream["segments"]:
                            if((seg['seg_type'] == 'ad') and (seg["period_id"] == merged_seg['period_id'])): #filter on current period only
                                for AdaptationSet in ad_tpl.find(ns("Period")):
                                    AdaptationSet1=deepcopy(AdaptationSet)
                                    contentType=AdaptationSet1.attrib["contentType"]
                                    if not (self.merged_streams['video'][1]['content_type'] == contentType): continue #TODO dynamically select one stream with AD

                                    AdaptationSet1.attrib["id"]=str(ar_count)
                                    AdPeriod.append(AdaptationSet1)

                                    Representation=AdaptationSet1.find(ns("Representation"))
                                    Representation.attrib["id"]=str(ar_count)
                                    Representation.attrib["bandwidth"]=merged_stream['bandwidth']
                                    Representation.attrib["width"]=merged_stream['resolution'].width
                                    Representation.attrib["height"]=merged_stream['resolution'].height

                                    ar_count=ar_count+1
                                    
                                    SegmentTemplate=Representation.find(ns("SegmentTemplate"))
                                    SegmentTemplate.attrib["timescale"] = str(seg["timescale"]) #TODO also set attribute 'duration' ?
                                    for f in ["initialization","media"]:
                                        SegmentTemplate.attrib[f]=seg[f] #TODO update again SegmentTemplate attributes (initialization, media) based on transcoding & user path stored ad

                                    #TODO SET SEGMENT_TIMELINE
            
                #We only need to update current period informations based on one stream selection only
                if merged_seg['seg_type'] == 'main':
                    #period per period from origin manifest
                    for op in origin_periods:
                        if (op.get('id') == merged_seg['old_period_id']): #required to map properly updated data from merged stream with corresponding original manifest 
                            #update period: set period with calculate (id, start) from merged streams seg
                            Period1=ET.SubElement(
                                self.manifest,
                                ns("Period"),
                                {
                                    "id":str(merged_seg['period_id']),
                                    "start":str(iso8601(merged_seg['period_start'])) #TODO duration or start?
                                }
                            )

                            #stream per stream apply copy from origin manifest
                            for AdaptationSet in op:
                                AdaptationSet1=ET.SubElement(Period1,ns("AdaptationSet"),AdaptationSet.attrib)
                                AdaptationSet1.attrib["id"]=str(ar_count)

                                Representation1=ET.SubElement(AdaptationSet1,ns("Representation"),AdaptationSet.find(ns("Representation")).attrib)
                                Representation1.attrib["id"]=str(ar_count)

                                ar_count=ar_count+1

                                #segments
                                SegmentTemplate1=ET.SubElement(Representation1,ns("SegmentTemplate"),AdaptationSet.find(ns("Representation")+"/"+ns("SegmentTemplate")).attrib)
                                SegmentTemplate1.attrib["presentationTimeOffset"]=op#[AdaptationSet][0][0] TODO?

                                #TODO SET SEGMENT_TIMELINE

                            continue
        
        print('DashMainManifestEditor#to_mpd#FINAL MANIFEST: ')
        print(ET.tostring(self.manifest,encoding='utf-8',method='xml'))

    #export as mpd file
    def to_file(self, segments, output_dir, filename):
        # Create dir
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)

        # Create file
        with open(output_dir + os.sep + filename, "w") as output_file:
            output_file.write()

##**Personalized Dash Manifest**##
#NOTE => for now the main goal is to be able to parse mpd with segmentsTLs and insert ADs based on period instead of segment partial duration, so no calcul required based on segs. In the case we evolve based on segments partials maybe we could transcode video mezzanine into segments playlists as HLS

##Video Content merge with Periodic Ads placement##
#video content manifest (multi periods)
print('read main video dash MPD...')
dmPlist = DashMasterPlaylistReader('./video-storage/dash/my_video/index.mpd').process_stream()
print('\n')

#ad video manifest
print('read ad dash MPD...')
ADdmPlist = DashMasterPlaylistReader('./video-storage/dash/vast_intro/index.mpd').process_stream()
print('\n')

#merge main content with ads
print('proceed merge...')
merged_manifests = DashMerger(dmPlist,[{"master": ADdmPlist, "timestamp": 31.033}])
merged_manifests.process_streams()

#TODO THEN => Personalized Manifest: Export/Write obj -> mpd + Calcul (mediaPresentationDuration,...)
final_manifest = DashMainManifestEditor('./video-storage/dash/my_video/index.mpd', merged_manifests.output_streams,None).to_mpd()
#personalized_master = merged_manifests.export()

##**---------------------------**##