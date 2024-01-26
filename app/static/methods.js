let scores = []
let endWorkout = false

const wait = (n) => new Promise((resolve) => setTimeout(resolve, n))

async function toggleRep(start=true, exercise) {
    const postData = {
        method: (start) ? "start-workout" : "end-workout",
        exercise: exercise,
    }

    console.log('Sending fetch get request to change method.')
    const response = await fetch("http://127.0.0.1:5000/video", {
      method: "POST",
      mode: "cors",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(postData),
    })

    console.log('Receiving response.')
    const data = await response.json()
    console.log(data['message'])

    // reloads iframe
    console.log('Reloading iframe.')
    $('#webcam').attr('src', function(i, val) {return val})

    if (!start) {
        while (true) {
            let response = await fetch("http://127.0.0.1:5000/get-model-response", {
                method: "GET",
                mode: "cors",
            })    

            let data = await response.json()
            console.log(`Prediction: ${data['response']}`)
            
            if (data['response'] != NaN) {
                console.log('Prediction wasnt empty; ending rep.')
                let prediction = Number(data['response'])*100
                scores.push(prediction)
                $('#accuracy-score').text(`${prediction}%`)
                return prediction
            } else {
                console.log('Prediction was empty sending another fetch.')
                await wait(500)
            }
        }
    }
}

async function startWorkout() {
    $('#begin-workout').prop('disabled',true)
    $('#end-workout').prop('disabled',false)
    scores = []
    endWorkout = false

    let exercise = $('#exercise-type').find(":selected").val()
    let reps = parseInt($('#exercise-reps').val())
    let repSpeed = parseInt($('#rep-speed').find(":selected").val())
    let sets = parseInt($('#exercise-sets').val())
    let breakLen = $('#exercise-breaks').val()

    if (!reps || !repSpeed || !sets || !breakLen) {
        alert("Fill in all inputs.")
        $('#begin-workout').prop('disabled',false)
        $('#end-workout').prop('disabled',true)
        return
    }
    
    let countdown = $('<h1></h1>')
    for (let i = 5; i > 0; i--) {
        countdown.text(`Starting workout in ${i}...`)
        console.log(i)
        $('#webcam-container').before(countdown)
        await wait(1000)
    }
    countdown.remove()
    console.log('Begun workout.')

    for (let set = 0; set < sets; set++) {
        console.log(`Beginning set ${set}`)
        for (let rep = 0; rep < reps; rep++) {
            console.log(`Beginning rep ${rep}`)
            toggleRep(true, exercise)
            countdown = $('<h1></h1>')
            countdown.attr("id","webcam-header")
            for (let i = repSpeed; i > 0; i--) {
                countdown.text(`Ending rep in ${i}...`)
                console.log(i)
                $('#webcam-container').before(countdown)
                await wait(1000)
                console.log(endWorkout)
                if (endWorkout) { return }
            }
            countdown.remove()
            toggleRep(false, exercise)
            await wait(500)
        }
        if (endWorkout) { return }
        countdown = $('<h1></h1>')
        countdown.attr("id","webcam-header")
        for (let i = breakLen; i > 0; i--) {
            countdown.text(`Starting new set in ${i}...`)
            console.log(i)
            $('#webcam-container').before(countdown)
            await wait(1000)
        }
        countdown.remove()
    }

    let header = $('<h1>Workout complete!</h1>')
    header.attr("id","completion-header")
    $('#webcam-container').before(header)

    console.log(`Prediction scores: ${scores}`)
    let avg = 0
    for (const score of scores) {
        avg += score
    }
    avg /= scores.length

    $('#full-score').text(`Average accuracy score: ${avg}%`)
    $('#begin-workout').prop('disabled',false)
}

async function stopWorkout() {
    $('#end-workout').prop('disabled',true)
    endWorkout = true
    $('#webcam-header').remove()
     
    await wait(5000)
    $('#begin-workout').prop('disabled',false)
}