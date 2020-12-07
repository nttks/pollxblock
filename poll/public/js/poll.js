/* Javascript for PollBlock. */

function PollUtil (runtime, element, pollType) {
    var self = this;
    var exportStatus = {};

    this.init = function() {
        // Initialization function used for both Poll Types
        this.voteUrl = runtime.handlerUrl(element, 'vote');
        this.tallyURL = runtime.handlerUrl(element, 'get_results');
        this.csv_url= runtime.handlerUrl(element, 'csv_export');
        this.votedUrl = runtime.handlerUrl(element, 'student_voted');
        this.submit = $('input[type=button]', element);
        this.answers = $('input[type=radio]', element);
        this.errorMessage = $('.error-message', element);

        // Set up gettext in case it isn't available in the client runtime:
        if (typeof gettext == "undefined") {
            window.gettext = function gettext_stub(string) { return string; };
            window.ngettext = function ngettext_stub(strA, strB, n) { return n == 1 ? strA : strB; };
        }

        // Make gettext available in Handlebars templates
        Handlebars.registerHelper('i18n', function(str) {
            return gettext(str);
        });

        // Make ngettext available in Handlebars templates
        Handlebars.registerHelper('i18n_ngettext', function(singular, plural, count) {
            return ngettext(singular, plural, count);
        });

        // Add helper for interpolating values into strings in Handlebars templates
        Handlebars.registerHelper('interpolate', function(formatString, parameters) {
            parameters = parameters.hash;
            return formatString.replace(/{\w+}/g,
                function(parameter) {
                    var parameterName = parameter.slice(1, -1);
                    return String(parameters[parameterName]);
                });
        });


        // Add helper for equality check
        Handlebars.registerHelper('if_eq', function(a, b, opts) {
            if(a == b)
                return opts.fn(this);
            else
                return opts.inverse(this);
        });

        this.resultsTemplate = Handlebars.compile($("." + pollType + "-results-template", element).html());

        this.viewResultsButton = $('.view-results-button', element);
        this.viewResultsButton.click(this.getResults);

        this.exportResultsButton = $('.export-results-button', element);
        this.exportResultsButton.click(this.exportCsv);

        this.downloadResultsButton = $('.download-results-button', element);
        this.downloadResultsButton.click(this.downloadCsv);

        return this.shouldDisplayResults();
    };

    this.pollInit = function(){
        // Initialization function for PollBlocks.
        var selector = 'input[name=choice]:checked';
        var radio = $(selector, element);
        self.submit.click(function () {
            // Disable the submit button to avoid multiple clicks
            self.disableSubmit();
            // We can't just use radio.selector here because the selector
            // is mangled if this is the first time this XBlock is added in
            // studio.
            radio = $(selector, element);
            var choice = radio.val();
            var thanks = $('.poll-voting-thanks', element);
            thanks.addClass('poll-hidden');
            // JQuery's fade functions set element-level styles. Clear these.
            thanks.removeAttr('style');
            $.ajax({
                type: "POST",
                url: self.voteUrl,
                data: JSON.stringify({"choice": choice}),
                success: self.onSubmit
            });
        });
        // If the user has already reached their maximum submissions, all inputs should be disabled.
        if (!$('div.poll-block', element).data('can-vote')) {
            $('input', element).attr('disabled', true);
        }
        // If the user has refreshed the page, they may still have an answer
        // selected and the submit button should be enabled.
        var answers = $('input[type=radio]', element);
        if (! radio.val()) {
            answers.bind("change.enableSubmit", self.enableSubmit);
        } else if ($('div.poll-block', element).data('can-vote')) {
            self.enableSubmit();
        }
    };

    this.surveyInit = function () {
        // Initialization function for Survey Blocks

        // If the user is unable to vote, disable input.
        if (! $('div.poll-block', element).data('can-vote')) {
            $('input', element).attr('disabled', true);
            return
        }
        self.answers.bind("change.enableSubmit", self.verifyAll);
        self.submit.click(function () {
            // Disable the submit button to avoid multiple clicks
            self.disableSubmit();
            $.ajax({
                type: "POST",
                url: self.voteUrl,
                data: JSON.stringify(self.surveyChoices()),
                success: self.onSubmit,
                complete: self.onComplete,
            });
        });
        // If the user has refreshed the page, they may still have an answer
        // selected and the submit button should be enabled.
        self.verifyAll();
    };

    this.shouldDisplayResults = function() {
        return $.ajax({
            // Semantically, this would be better as GET, but we can use helper
            // functions with POST.
            type: "POST",
            url: self.votedUrl,
            data: JSON.stringify({})
        });
    };

    this.surveyChoices = function () {
        // Grabs all selections for survey answers, and returns a mapping for them.
        var choices = {};
        self.answers.each(function(index, el) {
            el = $(el);
            choices[el.prop('name')] = $(self.checkedElement(el), element).val();
        });
        return choices;
    };

    this.checkedElement = function (el) {
        // Given the DOM element of a radio, get the selector for the checked element
        // with the same name.
        return "input[name='" + el.prop('name') + "']:checked"
    };

    this.verifyAll = function () {
        // Verify that all questions have an answer selected.
        var doEnable = true;
        self.answers.each(function (index, el) {
            if (! $(self.checkedElement($(el)), element).length) {
                doEnable = false;
                return false
            }
        });
        if (doEnable){
            self.enableSubmit();
        }
    };

    this.onSubmit = function (data) {
        // Fetch the results from the server and render them.
        if (!data['success']) {
            alert(data['errors'].join('\n'));
        }
        var can_vote = data['can_vote'];
        $('.poll-current-count', element).text(data['submissions_count']);
        $('.poll-max-submissions', element).text(data['max_submissions']);
        if (data['max_submissions'] > 1) {
            $('.poll-submissions-count', element).show();
        }
        if (data.restricted_list !== 'undefined') {
              $('.progress_restriction_info .restricted').data('list', data.restricted_list);
            }
        var restricted_chapters = data.restricted_chapters;
        if (restricted_chapters !== 'undefined'){
            $('.section-name').prop('disabled', false);
            for (var chapter_idx in restricted_chapters){
              if( restricted_chapters.hasOwnProperty(chapter_idx) ) {
                $($('.section-name')[restricted_chapters[chapter_idx]]).prop('disabled', true);
              }
            }
        }
        var restricted_sections = data.restricted_sections;
        if (restricted_sections !== 'undefined'){
            $('.subsection-text').prop('disabled', false);
            for (var sections in restricted_sections){
              if( restricted_sections.hasOwnProperty(sections) ) {
                $($('.subsection-text')[restricted_sections[sections]]).prop('disabled', true);
              }
            }
        }
        var restricted_verticals = data.restricted_verticals;
        $('.vertical-name').removeClass('vertical_restricted');
        if (restricted_verticals !== 'undefined') {
            for (var vertical_idx in restricted_verticals) {
              if (restricted_verticals.hasOwnProperty(vertical_idx)) {
                $($('.vertical-name')[restricted_verticals[vertical_idx]]).addClass('vertical_restricted');
              }
            }
        }
        if ($('div.poll-block', element).data('private')) {
            // User may be changing their vote. Give visual feedback that it was accepted.
            var thanks = $('.poll-voting-thanks', element);
            thanks.removeClass('poll-hidden');
            thanks.fadeOut(0).fadeIn('slow', 'swing');
            $('.poll-feedback-container', element).removeClass('poll-hidden');
            if (!can_vote) {
                // Disable all types of input within the element,
                // Radio button choices and the submit button.
                $('input', element).attr('disabled', true);
            } else {
                // Enable the submit button.
                self.enableSubmit();
            }
            return;
        }
        // Used if results are not private, to show the user how other students voted.
        self.getResults();
    };

    this.onComplete = function () {
        // [Issue#7] Update attendance status
        var updateAttendanceStatusUrl = ($('div.poll-block', element).data('update-attendance-status-url') || '')
            .replace('{}', $(element).data('course-id'));
        if (updateAttendanceStatusUrl) {
            $.ajax({
                type: "POST",
                url: updateAttendanceStatusUrl,
                headers: {'X-CSRFToken': $.cookie('csrftoken')},
            }).error(function () {
                console.log('Error update attendance status');
            });
        }
    };

    function getStatus() {
        $.ajax({
            type: 'POST',
            url: runtime.handlerUrl(element, 'get_export_status'),
            data: '{}',
            success: updateStatus,
            dataType: 'json'
        });
    }

    function updateStatus(newStatus) {
        var statusChanged = ! _.isEqual(newStatus, exportStatus);
        exportStatus = newStatus;
        if (exportStatus.export_pending) {
            // Keep polling for status updates when an export is running.
            setTimeout(getStatus, 1000);
        }
        if (statusChanged) {
            if (newStatus.last_export_result.error) {
                self.errorMessage.text(error);
                self.errorMessage.show();
            } else {
                self.downloadResultsButton.attr('disabled', false);
                self.errorMessage.hide()
            }
        }
    }

    this.exportCsv = function() {
        $.ajax({
            type: "POST",
            url: self.csv_url,
            data: JSON.stringify({}),
            success: updateStatus
        });
    };
    this.downloadCsv = function() {
        window.location = exportStatus.download_url;
    };

    this.getResults = function () {
        // Used if results are not private, to show the user how other students voted.
        function adjustGaugeBackground() {
            // Adjust the height of the grey background of the the percentage gauges.  This
            // couldn't be achieved with CSS.
            $('ul.poll-results > li', element).each(function() {
                var height = 0, width;
                $(this).children().each(function() {
                    height = Math.max(height, $(this).height());
                });
                width = $('.percentage-gauge-container', this).width();
                $('.percentage-gauge-background', this).height(height).width(width);
            });
        }
        function whenImagesLoaded(callback) {
            // Wait for all images to be loaded, then call callback.
            var missingImages = 1;
            $('img', element).each(function() {
                if ($(this).height() == 0) {
                    missingImages++;
                    $(this).load(function() {
                        if (--missingImages == 0) callback();
                    });
                }
            });
            if (--missingImages == 0) callback();
        }
        $.ajax({
            // Semantically, this would be better as GET, but we can use helper
            // functions with POST.
            type: "POST",
            url: self.tallyURL,
            data: JSON.stringify({}),
            success: function (data) {
                $('div.poll-block', element).html(self.resultsTemplate(data));
                $('.poll-results-wrapper', element).focus();
                whenImagesLoaded(adjustGaugeBackground);
            }
        });
    };

    this.disableSubmit = function() {
        // Disable the submit button.
        self.submit.attr("disabled", true);
    }

    this.enableSubmit = function () {
        // Enable the submit button.
        self.submit.removeAttr("disabled");
        self.answers.unbind("change.enableSubmit");
    };

    var init_map = {'poll': self.pollInit, 'survey': self.surveyInit};
    this.init().done(function(data) {
        // If the submit button doesn't exist, the user has already
        // selected a choice. Render results instead of initializing machinery.
        if (data['voted'] && ! data['private_results']) {
            self.onSubmit({'success': true});
            $('.poll-block-form-wrapper', element).hide();
        }
        else {
            $('.poll-block-form-wrapper', element).show();
            var max_submissions = parseInt($('.poll-max-submissions', element).text());
            var current_count = parseInt($('.poll-current-count', element).text());
            if (max_submissions > 1 && current_count > 0) {
                $('.poll-submissions-count', element).show();
            }
        }
    }).always(function(){
        init_map[pollType]();
    });
}

function PollBlock(runtime, element) {
    new PollUtil(runtime, element, 'poll');
}

function SurveyBlock(runtime, element) {
    new PollUtil(runtime, element, 'survey');
}
