NAME = 'Media CCC'
ICON = 'icon-default.png'
ART = 'art-default.jpg'

BASE_URL = 'http://api.media.ccc.de/public/'

def Start():
    ObjectContainer.title1 = NAME
    ObjectContainer.art = R(ART)

    # Setup the default attributes for the other objects
    DirectoryObject.thumb = R(ICON)
    DirectoryObject.art = R(ART)
    VideoClipObject.thumb = R(ICON)
    NextPageObject.thumb = R(ICON)

    HTTP.CacheTime = 300

@handler('/video/mediaccc', NAME, allow_sync=True)
def showDir(subdir = ''):
    data = JSON.ObjectFromURL(BASE_URL + 'conferences')

    oc = ObjectContainer()

    subdirs = set()
    if subdir == '':
        depth = 0
    else:
        depth = len(subdir.split('/'))
        top, down, children = split_pathname(subdir,depth - 1)
        oc.title2 = down.title();

    folders = []
    conferences = []

    for conference in sorted(data['conferences'], key=lambda conference: conference['webgen_location']):
        top, down, children = split_pathname(conference['webgen_location'], depth)

        if top != subdir or down in subdirs:
            continue

        if children:
            folders.append(DirectoryObject(key=Callback(showDir, subdir = build_path(top,down)), title = down.title(), thumb = R(ICON)))
            subdirs.add(down)
        else:
            conferences.append(DirectoryObject(key=Callback(showConference, acronym = conference['acronym']), title = conference['title'], thumb = Resource.ContentsOfURLWithFallback(url=conference['logo_url'], fallback=ICON)))

    for folder in folders:
        oc.add(folder)

    for conference in conferences:
        oc.add(conference)

    return oc

@route('/video/mediaccc/conference')
def showConference(acronym):
    data = JSON.ObjectFromURL(BASE_URL + 'conferences')
    conference = [x for x in data['conferences'] if x['acronym'] == acronym][0]

    title = "%s"%(conference['title'])
    oc = ObjectContainer(title2=title)

    # {"acronym":"eh2010",
    # "aspect_ratio":"16:9",
    # "updated_at":"2014-07-01T13:51:22.610+02:00",
    # "title":"Easterhegg 2010",
    # "schedule_url":"",
    # "webgen_location":"conferences/eh2010",
    # "logo_url":"http://static.media.ccc.de/media/conferences/eh2010",
    # "images_url":"http://static.media.ccc.de/media/conferences/eh2010",
    # "recordings_url":"http://cdn.media.ccc.de/events/eh2010",
    # "url":"http://api.media.ccc.de/public/conferences/5"},

    conf_data = JSON.ObjectFromURL(BASE_URL + 'conferences/' + conference['url'].rsplit('/', 1)[1])
    videos = conf_data['events']

    # {"guid":"import-c21113759a7e94d624",
    # "title":"Infrastrukturprojekte im µc³",
    # "subtitle":"Doku rund um die Projekte in den Münchner Clubräumen",
    # "slug":"EH2010-3776-de-inframuc3",
    # "link":"http://eh2010.muc.ccc.de/fahrplan/events/3776.en.html",
    # "description":"Ein virtueller Rundgang durch den Münchner Club um die Infrastruktur Projekte in mehr oder weniger chronologischer Reihenfolge vorzustellen: Luftschleuse, Matemat, Moodlamps, Hausbus, (Strom-)Verkabelung und Sonstiges.\n",
    # "persons":["Andi"],
    # "tags":["eh2010"],
    # "date":"2010-04-02T02:00:00.000+02:00",
    # "release_date":"2010-04-20",
    # "updated_at":"2014-08-05T09:42:09.588+02:00",
    # "length":3195,
    # "thumb_url":"http://static.media.ccc.de/media/conferences/eh2010/EH2010-3776-de-inframuc3.jpg",
    # "poster_url":"http://static.media.ccc.de/media/conferences/eh2010/EH2010-3776-de-inframuc3_preview.jpg",
    # "frontend_link":"http://media.ccc.de/browse/conferences/eh2010/EH2010-3776-de-inframuc3.html",
    # "url":"http://api.media.ccc.de/public/events/210",
    # "conference_url":"http://api.media.ccc.de/public/conferences/5"},

    for video in videos:
        event = video['url'].rsplit('/', 1)[1] 

        oc.add(CreateVideoClipObject(video = video))

    return oc

@route('/video/mediaccc/event')
def showEvent(event):
    data = JSON.ObjectFromURL(BASE_URL + 'events/' + event)
    want = sorted(filter(is_video, data['recordings']), key=format_priority)

    if len(want) > 0:
        return Redirect(want[0]['recording_url'])

@route('/video/mediaccc/eventcontainer')
def showEventContainer(event):
    data = JSON.ObjectFromURL(BASE_URL + 'events/' + event)
    url = Callback(showEvent, event=event)

    videoclip_obj = CreateVideoClipObject(video = data)

    items = []
    for media in sorted(filter(is_video,data['recordings']), key=format_priority):
        # todo show all content
        if media['mime_type'] != 'video/mp4':
            continue

        items.append(
            MediaObject(
                parts = [
                    PartObject(key=url)
                ],
                container = Container.MP4,
                video_codec = VideoCodec.H264,
                video_resolution = media['height'],#'576',
                audio_codec = AudioCodec.AAC,
                audio_channels = 2,
                optimized_for_streaming = True
            )
        )
    
    videoclip_obj.items = items

    return ObjectContainer(objects=[videoclip_obj])

def CreateVideoClipObject(video):
    event = video['url'].rsplit('/', 1)[1]
    url = Callback(showEvent, event=event)

    videoclip_obj = VideoClipObject(
        key = Callback(showEventContainer, event = event), 
        rating_key = url,
        title = video['title'],
        thumb = Resource.ContentsOfURLWithFallback(url=video['poster_url'], fallback=ICON),
        tags = video['tags'],
        duration = video['length']*1000,
        source_title = "CCC",
        originally_available_at = Datetime.ParseDate(video['date']),
        year = int(video['release_date'].split('-')[0]),
        summary = video['description'],
        items = [
            MediaObject(
                parts = [
                    PartObject(key=url)
                    ],
                container = Container.MP4,
                video_codec = VideoCodec.H264,
                video_resolution = '576', ## we do not know the resolution so we set it to 576
                audio_codec = AudioCodec.AAC,
                audio_channels = 2,
                optimized_for_streaming = True
            )
        ]
    )

    return videoclip_obj

def build_path(top, down):
    if top == '':
        return down
    else:
        return '/'.join((top, down))

def split_pathname(name, depth):
    path = name.split('/')
    top = '/'.join(path[0:depth])
    if depth < len(path):
        down = path[depth]
    else:
        down = None
    children = len(path)-1 > depth
    return (top, down, children)

def is_video(entry):
    return entry['mime_type'].startswith('video/')

def format_priority(entry):
    enc = entry['mime_type'].split('/')[1]
    if enc == 'mp4':
        return 1 # Can be hardware-accelerated
    elif enc == 'webm':
        return 2
    else:
        return 99
