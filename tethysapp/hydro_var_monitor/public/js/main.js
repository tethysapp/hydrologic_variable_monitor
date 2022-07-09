const App = (() => {
    'use strict';
    // Global variables from base.html
    // URL_GETMAPID - string, url of api call to get tile layer url
    // SOURCES - JSON of ee sources by variable
    const URL_OPENSTREETMAP = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"

    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value

    const selectVariable = document.getElementById("select-variable")
    const selectSource = document.getElementById("select-source")
    const btnLoadMap = document.getElementById("load-map")
    const btnClearMap = document.getElementById("clear-map")
    const btnPlotSeries = document.getElementById("plot-series")

    const map = L.map("map", {
        zoom: 3,
        minZoom: 2,
        boxZoom: true,
        maxBounds: L.latLngBounds(L.latLng(-100, -225), L.latLng(100, 225)),
        center: [20, 0]
    })
    const basemaps = {"Open Street Map": L.tileLayer(URL_OPENSTREETMAP).addTo(map)}
    const eeTileLayer = L.tileLayer("").addTo(map)
    let eeTileLayerName = "Earth Engine Layer"
    const mapCtrls = L.control.layers(basemaps, {eeTileLayerName: eeTileLayer}).addTo(map);

    const getVarSourceJSON = () => {
        return {
            "variable": selectVariable.value,
            "source": selectSource.value
        }
    }

    btnLoadMap.onclick = () => {
        const fetchParams = {
            method: "POST",
            headers: {'X-CSRFToken': csrftoken},
            body: JSON.stringify(getVarSourceJSON())
        }

        if (fetchParams.body.variable === "" || fetchParams.body.source === "") return

        fetch(URL_GETMAPID, fetchParams)
            .then(response => response.json())
            .then(map_url => {
                eeTileLayer.setUrl(map_url.url)
            })
            .catch(error => console.log(error))
            .finally(() => {
            })
    }

    selectVariable.onchange = (e) => {
        selectSource.innerHTML = SOURCES[e.target.value].map(src => `<option value="${src}">${src}</option>`).join("")
    }
    return {}
})();