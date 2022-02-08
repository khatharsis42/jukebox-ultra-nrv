/**
Script managing the interface.
It uses JQuery

It is used to load the Youtube iframe, refresh the playlist and suggestion column.
 */

/**
 *
 * @param html: html of the page
 * @param d: dictionary of key values which will replace { key } in html
 * @returns a html, with values replacing keys
 */
function template(html, d) {
    let r = html;
    for (let i in d) {
        if (i=="title") { // track title appears both on verso and recto, so we replace in the if and after
            r=r.replace("{"+i+"}", d[i]);
        }
        r=r.replace("{"+i+"}", d[i]);
    }
    r=r.replace(/{\w+}/g, "");
    return r;
}


/**
 * Called on click of the buttons which switch the recto/verso of song tiles.
 * These buttons are .btn-more and .btn-back.
 */
function toggle_recto_verso() {
    let track_li = $(this).closest("li");
    track_li.find(".verso").toggle();
    track_li.find(".recto").toggle();
}


/**
 * Generate the HTML for a track tile
 *
 * @param t: dictionary representing a serialized Track
 * @returns {jQuery|HTMLElement} : html for the tile
 */
function generate_track_html(t) {
    let track_html = $(template(track_template, t));
    track_html.data("track", t); // we add the serialized object as data to the tile
    track_html.find(".verso").hide();
    track_html.find(".btn-more").click(toggle_recto_verso);
    track_html.find(".btn-back").click(toggle_recto_verso);
    track_html.find(".btn-top").click(function() {
        $.post("/move-track", {"action": "top", "randomid": t["randomid"]});
    });
    track_html.find(".btn-up").click(function() {
        $.post("/move-track", {"action": "up", "randomid": t["randomid"]});
    });
    track_html.find(".btn-down").click(function() {
        $.post("/move-track", {"action": "down", "randomid": t["randomid"]});
    });

    track_html.find(".btn-refresh").click(function() {
        $.post("/refresh-track", {"url": t["url"]});
    });
    return track_html
}

/**
 * Generate the HTML for a track tile in the suggestion column.
 * It deactivate the buttons to move the track, and the one to remove it.
 *
 * @param t : dict, serialized Track
 * @returns {jQuery|HTMLElement} : html for the tile
 */
function generate_track_html_suggest(t) {
    let track_html = generate_track_html(t);
    track_html.find(".btn-add").click(function() {
        $.post("/add", t);
    });
    track_html.find(".btn-remove").remove();
    track_html.find(".btn-up").remove();
    track_html.find(".btn-down").remove();
    track_html.find(".btn-top").remove();
    return track_html;
}


/**
 * Generate the HTML for a track tile in the queue.
 * It deactivate the button to remove the track.
 *
 * @param t : dict, serialized Track
 * @returns {jQuery|HTMLElement} : html for the tile
 */
function generate_track_html_queue(t) {
    let track_html = generate_track_html(t);
    track_html.find(".btn-remove").click(function() {
        console.log("Removing track with randomid: ", t["randomid"]);
        $.post("/remove", t);
    });
    track_html.find(".btn-add").remove();
    return track_html;
}


track_template = `
<li class="list-group-item track" id="{randomid}">
    <div class="row recto">
        <div class="col-4 centered">
            <img class="albumart" src="{albumart_url}">
        </div>
        <div class="col track-info centered">
            <span class="track-title">{title}</span>
            <span class="track-artist">{artist}</span>
            <span class="track-duration">{duration} s.</span>
            <span class="track-user float-right">Added by {user}</span>
        </div>
        <div class="col-1">
            <button class="icon btn-more" alt="More"></button>
            <button class="icon btn-add" alt="Play"></button>
            <button class="icon btn-top" alt="Top"></button>
            <button class="icon btn-up" alt="Up"></button>
            <button class="icon btn-down" alt="Down"></button>
            <button class="icon btn-remove" alt="Enlever"></button>
        </div>
     </div>
     <div class="row verso">
        <div class="col">
            <span class="track-title">{title}</span>
            <span class="track-url"><a href="{url}">Link to media</a></span>
            <span class="track-album">Album : {album}</span>
            <span class="track-source">From {source}</span>
        </div>
        <div class="col-1">
            <button class="icon btn-back" alt="Back"></button>
            <button class="icon btn-refresh" alt="Refresh"></button>
        </div>
    </div>
</li>
`;

// We load the Youtube iframe
const tag = document.createElement('script');
tag.src = "https://www.youtube.com/iframe_api";
const firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

let pause = false;
let yt = 0;
function onYouTubeIframeAPIReady() {
    yt = new YT.Player('YT', {
        height: '360',
        width: '640',
        events: {
            'onReady': function() {
                console.log("YT ready");
                yt.mute();
                yt.ready = true; 
                $('#pause').on("click", function() {
                    if (pause) {yt.playVideo();} else {yt.pauseVideo();}
                    pause = ! pause;
                    $.post('/pause_play');
                    return true;
                });
                
                $('#rewind').on("click", function() {
                    yt.seekTo(0);
                    $.post('rewind');
                    return true;
                });
            }
        }

    });
}

/**
 * Synchronizes the video from Youtube iframe with the sound from mpv.
 *
 * @param mpv_time : float : timestamp of mpv
 */
function syncVideo(mpv_time) {
    if (mpv_time === 0) {
        yt.pauseVideo();
    } else {
        let ytTime = yt.getCurrentTime();
        if (! pause) {yt.playVideo();}
        let delta = ytTime - mpv_time;
        if (Math.abs(delta) > 1) {
            yt.seekTo(mpv_time);
        }
    }
}

/**
 * Updates the playlist
 * Also calls the function updating the Youtube iframe.
 *
 * Careful when editing, this function works fine, but may be a bit messy.
 * @param data: dict given by /sync
 */
function updates_playlist(data) {
    // we first get the current playlistHTML
    let playlist = data.playlist;
    let playlistHTML = $("#playlist");
    // then we must check that all elements in playlist are in playlistHTML
    if (playlist.length === 0) {
        playlistHTML.children().remove();
        return;
    }

    /* so we browse the playlist dict
    If the track in the html corresponds to the current one in the dict, it's fine.
    Else we remove the track in HTML and put the one in the dict.
    We don't "move" the html tiles, we just delete them wherever they are wrong.
    */
    for (let i=0; i<playlist.length; i++) {
        let track = playlist[i];
        if (i === 0 && (playlistHTML.find(".track") === 0 || playlistHTML.find(".track:first").attr("id") != track.randomid)) {
            if (playlistHTML.find(".track").length !== 0) {
                playlistHTML.find(".track:first").remove();
            }
            if (playlistHTML.find("#playlist-playing").length !== 0) {
                playlistHTML.find("#playlist-playing").remove();
            }
            playlistHTML.prepend(generate_track_html_queue(track));
            playlistHTML.find(".track:first .btn-down").hide();
            playlistHTML.find(".track:first .btn-up").hide();
            playlistHTML.find(".track:first .btn-top").hide();

            // then we manage the Youtube iframe
            if (yt.ready && $("#YT").is(":visible") && track["source"] === "youtube") {
                let url = new URL(data.playlist[0]["url"]);
                let videoId = url.searchParams.get("v");
                let t;
                if (url.searchParams.has("t")) {
                    t = parseInt(url.searchParams.get("t"), 10);
                } else {
                    t = 0;
                }
                if (yt.url !== videoId) {
                    console.log("Loading video with id : ", videoId, " at time ", t);
                    yt.cueVideoById(new String(videoId), t);
                    yt.url = videoId;
                    yt.playVideo();
                }
                syncVideo(data.time);
            }
            if (playlistHTML.find("#playlist-playing").length === 0) { // it doesn't display
                console.log("Adding Lecture en cours");
                playlistHTML.find(".track:first").before("<li id='playlist-playing' class='playlist-title'>Now playing</li>");
            }
        }
        // we do not use !== as the elements are not the same types
        else if (playlistHTML.find(".track:last-child").index < i || playlistHTML.find(".track:eq("+i+")").attr("id") != track.randomid) {
            if (i===1) {
                playlistHTML.find("#playlist-queue").remove();
            }
            playlistHTML.find(".track:eq("+i+")").remove();
            let j = i-1;
            playlistHTML.find(".track:eq("+j+")").after(generate_track_html_queue(track));


            if (playlistHTML.find("#playlist-queue").length === 0) {
                playlistHTML.find(".track:eq(0)").after("<li id='playlist-queue' class='playlist-title'>Upcoming...</li>");
            }
        }
    }

    // we must remove elements in playlistHTML which are too much
    let i = playlist.length -1;
    let track_tile = playlistHTML.find(".track:eq("+i+")");
    while (track_tile.next().length !== 0) {
        track_tile = track_tile.next();
        track_tile.remove();
    }
}

/**
 * This is what happens when we GET /sync
 */
sync = function() {
    let time = Date.now() / 1000;
    $.get("/sync", function (data) {
        $('#volume-slider').val(data.volume);
        updates_playlist(data);
        if (yt !== 0) {
            syncVideo(data.time);
        }
    });
    window.setTimeout(arguments.callee, 1000);
}();

/**
 *
 */
let delay = (function(){
    let timer = 0;
    return function(callback, ms){
        clearTimeout (timer);
        timer = setTimeout(callback, ms);
    };
})();

/**
 * When pressing enter in the search bar, make a search.
 */
$('#query').keyup(function(e) {
    let code = e.which;
    // We make a search **only** if the enter key has been pressed
    if (code != 13) {
        return;
    }
    let query = $('#query').val().trim();
    if (query == "") {
        $("#search_results").html("");
        $("#search_results").hide();
        return;
    }
    delay(function() {
        console.log("searching "+$('#query').val());
        $.post("/search", {"q": query}, function(data) {
            $("#search_results").html("");
            for (let i=0; i<data.length; i++) {
                let track = data[i];
                console.log("Track :");
                console.log(track);
                $('#search_results').append(generate_track_html_suggest(track));
                $('#search_results li:last .btn-add').click(function() {
                    $('#query').val("");
                    $('#search_results').hide();
                });
            }
            $("#search_results").show()
        }, dataType="json");
        if ($('#query').val() == "") {
            $("#search_results").html("");
            $("#search_results").hide();
            return;
        }
    },250);
});

$('#query').focus(function () {
    if ($('#query').val() != "")
        $('#search_results').show();
});

/**
 * Get the suggested tracks
 */
function suggest() {
    $.get("/suggest", function (data) {
        $('#suggestions').html("");
        for (let i =0; i<data.length; i++) {
            let t = data[i];
            $('#suggestions').append(generate_track_html_suggest(t));
        }
    });
}

$("#volume-slider").change(function() {
    $.post("/volume", {"volume": $(this).val()})
});

$("#refresh-suggestions").click(suggest);

$("#toggle-YT").click(function() {
    $("#YT").toggle();
    if (!$("#YT").is(":visible")) {
        yt.stopVideo();
    } else {
        yt.playVideo();
    }
});

// we hide the search results by default
$('#search_results').hide();


$(document).ready(function() {
    suggest();
});


